import json
import os
import base64
import requests
from pathlib import Path
from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH
from constants import logger, HOME_DIR, LECTURE_URL

class AutoDRM:
    def __init__(self, udemy_instance, portal_name):
        self.udemy = udemy_instance
        self.portal_name = portal_name
        self.keys = {}
        self.device_path = Path(HOME_DIR) / "device.wvd"
        
        # Initialize Widevine CDM
        if self.device_path.exists():
            self.device = Device.load(self.device_path)
            self.cdm = Cdm.from_device(self.device)
            logger.info("Widevine CDM initialized successfully")
        else:
            logger.error(f"Device file {self.device_path} not found! Please ensure device.wvd exists.")
            raise FileNotFoundError(f"Device file not found: {self.device_path}")

    def find_wv_pssh_offsets(self, raw_bytes):
        """Find Widevine PSSH offsets in binary data"""
        offsets = []
        offset = 0
        while True:
            offset = raw_bytes.find(b'pssh', offset)
            if offset == -1:
                break
            size = int.from_bytes(raw_bytes[offset-4:offset], byteorder='big')
            pssh_offset = offset - 4
            offsets.append(raw_bytes[pssh_offset:pssh_offset+size])
            offset += size
        return offsets

    def extract_pssh_from_bytes(self, content_bytes):
        """Extract PSSH from binary content"""
        wv_offsets = self.find_wv_pssh_offsets(content_bytes)
        pssh_list = [base64.b64encode(wv_offset).decode() for wv_offset in wv_offsets]

        # Find the best PSSH (length between 20-220 chars)
        for pssh in pssh_list:
            if 20 < len(pssh) < 220:
                return pssh

        # If no good PSSH found, return the first one if available
        return pssh_list[0] if pssh_list else None

    def find_init_urls_in_mpd(self, mpd_url):
        """Find init file URLs in MPD manifest"""
        try:
            logger.info("Parsing MPD to find init file URLs...")

            response = self.udemy.request(mpd_url)
            response.raise_for_status()
            mpd_content = response.text

            # Look for initialization URLs in MPD
            import re

            # Pattern for initialization URLs
            init_patterns = [
                r'initialization="([^"]+)"',
                r'<Initialization[^>]*sourceURL="([^"]+)"',
                r'<SegmentBase[^>]*initialization="([^"]+)"'
            ]

            init_urls = []
            for pattern in init_patterns:
                matches = re.findall(pattern, mpd_content)
                init_urls.extend(matches)

            if init_urls:
                # Get base URL from MPD URL
                base_url = "/".join(mpd_url.split("/")[:-1]) + "/"

                # Convert relative URLs to absolute
                absolute_urls = []
                for url in init_urls:
                    if url.startswith("http"):
                        absolute_urls.append(url)
                    else:
                        absolute_urls.append(base_url + url)

                logger.info(f"Found {len(absolute_urls)} init URLs")
                return absolute_urls
            else:
                logger.warning("No init URLs found in MPD")
                return []

        except Exception as e:
            logger.error(f"Failed to parse MPD: {e}")
            return []

    def download_and_extract_pssh(self, mpd_url, temp_dir):
        """Download init file and extract PSSH (updated method)"""
        try:
            # First, try to find init URLs in MPD
            init_urls = self.find_init_urls_in_mpd(mpd_url)

            if not init_urls:
                logger.error("No init URLs found")
                return None

            # Try each init URL
            for i, init_url in enumerate(init_urls):
                try:
                    logger.info(f"Downloading init file {i+1}/{len(init_urls)}...")

                    response = self.udemy.request(init_url)
                    response.raise_for_status()

                    # Extract PSSH from downloaded content
                    logger.info("Extracting PSSH from init file...")
                    pssh_b64 = self.extract_pssh_from_bytes(response.content)

                    if pssh_b64:
                        logger.info(f"Extracted PSSH: {pssh_b64[:50]}...")
                        return pssh_b64
                    else:
                        logger.warning(f"No PSSH found in init file {i+1}")
                        continue

                except Exception as e:
                    logger.warning(f"Failed to download init file {i+1}: {e}")
                    continue

            logger.error("Failed to extract PSSH from any init file")
            return None

        except Exception as e:
            logger.error(f"Failed to extract PSSH from init file: {e}")
            return None



    def get_media_license_token(self, course_id, lecture_id):
        """Get media license token from lecture info"""
        try:
            import random
            lecture_url = LECTURE_URL.format(
                portal_name=self.portal_name,
                course_id=course_id,
                lecture_id=lecture_id,
                rand=random.random()
            )
            
            response = self.udemy.request(lecture_url)
            response.raise_for_status()
            lecture_data = response.json()
            
            asset = lecture_data.get('asset', {})
            media_license_token = asset.get('media_license_token')
            
            if media_license_token:
                logger.info(f"Retrieved media license token for lecture {lecture_id}")
                return media_license_token
            else:
                logger.warning(f"No media license token found for lecture {lecture_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get media license token: {e}")
            return None

    def extract_keys_from_license(self, pssh_b64, media_license_token):
        """Extract decryption keys using Widevine CDM (copy from working test file)"""
        try:
            logger.info("🔐 Using REAL Widevine CDM to extract keys...")

            # Decode PSSH
            pssh_data = base64.b64decode(pssh_b64)
            pssh = PSSH(pssh_data)

            kid = pssh.key_ids[0]
            logger.info(f"🔑 KID from PSSH: {kid}")

            # Open CDM session
            session_id = self.cdm.open()

            # Get license challenge
            challenge = self.cdm.get_license_challenge(session_id, pssh, "STREAMING", False)

            # Make license request (same URL format as udemy_downloader)
            license_url = f"https://{self.portal_name}.udemy.com/media-license-server/validate-auth-token?drm_type=widevine&auth_token={media_license_token}"

            logger.info("🔐 Making REAL license request...")
            response = requests.post(license_url, data=challenge)
            response.raise_for_status()

            logger.info(f"✅ License response status: {response.status_code}")

            # Parse license response
            self.cdm.parse_license(session_id, response.content)

            # Extract keys
            keys = self.cdm.get_keys(session_id, "CONTENT")

            # Find key that matches KID (same as udemy_downloader)
            key = next((k.key.hex() for k in keys if k.kid == kid), None)

            if key:
                kid_hex = kid.hex.replace("-", "")
                logger.info(f"🎉 REAL extracted key: {kid_hex}:{key}")

                # Close CDM session
                self.cdm.close(session_id)

                return {kid_hex: key}  # Return as dict with kid as key, key as value (compact format)
            else:
                logger.error("❌ Failed to find matching key")
                return {}

        except Exception as e:
            logger.error(f"❌ REAL key extraction failed: {e}")
            # If license server fails, try to use existing keys
            logger.warning("License server failed, checking for existing keys...")
            return {}

    def find_drm_lecture(self, course_id):
        """Find the first DRM-protected lecture in the course (optimized version)"""
        try:
            logger.info("🔍 Fast DRM detection using curriculum API...")

            # Use optimized curriculum URL with media_license_token field (like tampermonkey script)
            curriculum_url = f"https://{self.portal_name}.udemy.com/api-2.0/courses/{course_id}/subscriber-curriculum-items/?page_size=200&fields[lecture]=title,object_index,is_published,sort_order,created,asset,supplementary_assets,is_free&fields[quiz]=title,object_index,is_published,sort_order,type&fields[practice]=title,object_index,is_published,sort_order&fields[chapter]=title,object_index,is_published,sort_order&fields[asset]=title,filename,asset_type,status,time_estimation,media_license_token,is_external&caching_intent=True"

            response = self.udemy.request(curriculum_url)
            response.raise_for_status()
            curriculum_data = response.json()

            results = curriculum_data.get('results', [])

            # Filter lectures only
            lectures = [item for item in results if item.get('_class') == 'lecture']
            logger.info(f"📚 Found {len(lectures)} lectures in course")

            # Filter lectures with DRM (media_license_token is not null) - like tampermonkey script
            drm_lectures = [
                lecture for lecture in lectures
                if lecture.get('asset', {}).get('media_license_token') is not None
            ]

            if drm_lectures:
                logger.info(f"🔐 Found {len(drm_lectures)} DRM-protected lectures")

                # Try to get MPD URL from the first few DRM lectures quickly
                for i, drm_lecture in enumerate(drm_lectures[:3]):  # Try first 3 only
                    lecture_id = drm_lecture.get('id')
                    lecture_title = drm_lecture.get('title')

                    logger.info(f"✅ Trying DRM lecture {i+1}: {lecture_title} (ID: {lecture_id})")

                    try:
                        # Get the MPD URL by fetching lecture details
                        import random
                        lecture_url = LECTURE_URL.format(
                            portal_name=self.portal_name,
                            course_id=course_id,
                            lecture_id=lecture_id,
                            rand=random.random()
                        )

                        lecture_response = self.udemy.request(lecture_url)
                        lecture_response.raise_for_status()
                        lecture_data = lecture_response.json()

                        asset = lecture_data.get('asset', {})
                        media_sources = asset.get('media_sources', [])

                        # Find MPD source
                        for source in media_sources:
                            if source.get('type') == 'application/dash+xml':
                                mpd_url = source.get('src')
                                logger.info(f"🎯 Found MPD URL for DRM lecture")
                                return lecture_id, mpd_url

                        logger.warning(f"DRM lecture {i+1} has no MPD URL, trying next...")
                        continue

                    except Exception as e:
                        logger.warning(f"Failed to get MPD URL for lecture {i+1}: {e}")
                        continue

                logger.warning("No usable DRM lectures found with MPD URLs")
                return None, None
            else:
                logger.info("✅ No DRM-protected content found - course is DRM-free!")
                return None, None

        except Exception as e:
            logger.error(f"Failed to find DRM lecture: {e}")
            return None, None



    def extract_and_save_keys(self, course_id):
        """Main method to extract DRM keys and save to JSON"""
        try:
            import time
            start_time = time.time()

            logger.info("⚡ Fast DRM detection starting...")

            # Find first DRM lecture using optimized method
            lecture_id, mpd_url = self.find_drm_lecture(course_id)

            detection_time = time.time() - start_time
            logger.info(f"🚀 DRM detection completed in {detection_time:.2f} seconds")

            if not lecture_id or not mpd_url:
                logger.info("✅ Course is DRM-free - no key extraction needed!")
                return

            print()
            logger.info(f"Processing DRM lecture ID: {lecture_id}")

            # Create temp directory for download
            import tempfile
            temp_dir = tempfile.mkdtemp()

            try:
                # Download segment and extract PSSH
                pssh_b64 = self.download_and_extract_pssh(mpd_url, temp_dir)
                if not pssh_b64:
                    logger.error("Failed to extract PSSH from downloaded segment")
                    return
            finally:
                # Clean up temp directory
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            
            # Get media license token
            media_license_token = self.get_media_license_token(course_id, lecture_id)
            if not media_license_token:
                logger.error("Failed to get media license token")
                return
            
            # Extract keys
            extracted_keys = self.extract_keys_from_license(pssh_b64, media_license_token)

            # Always save to JSON file (even if empty, to avoid "Expecting value" error)
            keys_file = os.path.join(HOME_DIR, "drm_keys.json")

            # Load existing keys if file exists
            existing_keys = {}
            if os.path.exists(keys_file):
                try:
                    with open(keys_file, 'r') as f:
                        data = json.load(f)

                    # Support both old and new format
                    if isinstance(data, dict):
                        # Check if it's old format {"kid": "kid:key"} or new format {"kid": "key"}
                        first_key = next(iter(data.keys())) if data else None
                        if first_key and ":" in data[first_key]:
                            # Old format: {"kid": "kid:key"} -> convert to new format {"kid": "key"}
                            existing_keys = {}
                            for kid, kid_key in data.items():
                                if ":" in kid_key:
                                    key_part = kid_key.split(":", 1)[1]  # Get key part after ":"
                                    existing_keys[kid] = key_part
                            logger.info("🔄 Converted old key format to new compact format")
                        else:
                            # Already new format: {"kid": "key"}
                            existing_keys = data
                except:
                    existing_keys = {}

            if extracted_keys:
                # Replace with new keys only (as per user preference)
                existing_keys = extracted_keys

                # Save to file in compact format
                with open(keys_file, 'w') as f:
                    json.dump(existing_keys, f, indent=2)

                logger.info(f"✅ Successfully saved {len(extracted_keys)} keys to {keys_file}")

                # Display extracted keys
                for kid, key_value in extracted_keys.items():
                    logger.info(f"🔑 Key: {kid}:{key_value}")
            else:
                # Save existing keys to maintain file
                with open(keys_file, 'w') as f:
                    json.dump(existing_keys, f, indent=2)

                logger.warning("⚠️ No new keys extracted, but existing keys preserved")

                # Show existing keys if any
                if existing_keys:
                    logger.info(f"📋 Using {len(existing_keys)} existing keys:")
                    for kid, key_value in existing_keys.items():
                        logger.info(f"🔑 Key: {kid}:{key_value}")
                else:
                    logger.warning("❌ No DRM keys available")
                
        except Exception as e:
            logger.error(f"Failed to extract and save keys: {e}")
