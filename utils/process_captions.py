import os
import requests
import webvtt
from constants import logger

def find_best_language_match(available_captions, requested_languages):
    """Find the best matching language from available captions"""
    available_locales = [cap.get('locale_id', '') for cap in available_captions]

    # Create base language groups (language without country code)
    base_language_groups = {
        'en': ['en_US', 'en_GB', 'en_AU', 'en_CA', 'en_NZ', 'en_IE', 'en_ZA', 'en_IN'],
        'es': ['es_ES', 'es_MX', 'es_AR', 'es_CO', 'es_CL', 'es_PE', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_DO', 'es_CU', 'es_PR'],
        'pt': ['pt_BR', 'pt_PT'],
        'fr': ['fr_FR', 'fr_CA', 'fr_BE', 'fr_CH', 'fr_LU'],
        'de': ['de_DE', 'de_AT', 'de_CH', 'de_LU'],
        'zh': ['zh_CN', 'zh_TW', 'zh_HK', 'zh_SG'],
        'it': ['it_IT', 'it_CH'],
        'nl': ['nl_NL', 'nl_BE'],
        'ar': ['ar_SA', 'ar_EG', 'ar_AE', 'ar_MA', 'ar_DZ', 'ar_TN', 'ar_LB', 'ar_JO', 'ar_SY', 'ar_IQ', 'ar_KW', 'ar_QA', 'ar_BH', 'ar_OM', 'ar_YE', 'ar_LY', 'ar_SD'],
        'ru': ['ru_RU', 'ru_BY', 'ru_KZ', 'ru_KG', 'ru_UA'],
        'ja': ['ja_JP'],
        'ko': ['ko_KR'],
        'hi': ['hi_IN'],
        'ta': ['ta_IN'],
        'te': ['te_IN'],
        'bn': ['bn_IN', 'bn_BD'],
        'gu': ['gu_IN'],
        'mr': ['mr_IN'],
        'kn': ['kn_IN'],
        'ml': ['ml_IN'],
        'pa': ['pa_IN', 'pa_PK'],
        'ur': ['ur_PK', 'ur_IN'],
        'vi': ['vi_VN'],
        'th': ['th_TH'],
        'tr': ['tr_TR'],
        'pl': ['pl_PL'],
        'sv': ['sv_SE', 'sv_FI'],
        'no': ['no_NO', 'nb_NO', 'nn_NO'],
        'da': ['da_DK'],
        'fi': ['fi_FI'],
        'el': ['el_GR', 'el_CY'],
        'he': ['he_IL'],
        'fa': ['fa_IR', 'fa_AF'],
        'id': ['id_ID'],
        'ms': ['ms_MY', 'ms_BN'],
        'cs': ['cs_CZ'],
        'sk': ['sk_SK'],
        'hr': ['hr_HR'],
        'sr': ['sr_RS'],
        'bs': ['bs_BA'],
        'uk': ['uk_UA'],
        'hu': ['hu_HU'],
        'ro': ['ro_RO', 'ro_MD'],
        'bg': ['bg_BG'],
        'lt': ['lt_LT'],
        'lv': ['lv_LV'],
        'et': ['et_EE'],
        'sl': ['sl_SI'],
        'af': ['af_ZA'],
        'sw': ['sw_KE', 'sw_TZ'],
    }

    # Create comprehensive language mapping for fallbacks
    language_fallbacks = {
        # English variants
        'en_US': ['en_GB', 'en_AU', 'en_CA', 'en_NZ', 'en_IE', 'en_ZA', 'en_IN', 'en'],
        'en_GB': ['en_US', 'en_AU', 'en_CA', 'en_NZ', 'en_IE', 'en_ZA', 'en_IN', 'en'],
        'en_AU': ['en_GB', 'en_US', 'en_CA', 'en_NZ', 'en_IE', 'en_ZA', 'en_IN', 'en'],
        'en_CA': ['en_US', 'en_GB', 'en_AU', 'en_NZ', 'en_IE', 'en_ZA', 'en_IN', 'en'],
        'en_NZ': ['en_AU', 'en_GB', 'en_US', 'en_CA', 'en_IE', 'en_ZA', 'en_IN', 'en'],
        'en_IE': ['en_GB', 'en_US', 'en_AU', 'en_CA', 'en_NZ', 'en_ZA', 'en_IN', 'en'],
        'en_ZA': ['en_GB', 'en_US', 'en_AU', 'en_CA', 'en_NZ', 'en_IE', 'en_IN', 'en'],
        'en_IN': ['en_GB', 'en_US', 'en_AU', 'en_CA', 'en_NZ', 'en_IE', 'en_ZA', 'en'],

        # Spanish variants (complete Latin America + Spain)
        'es_ES': ['es_MX', 'es_AR', 'es_CO', 'es_CL', 'es_PE', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_MX': ['es_ES', 'es_AR', 'es_CO', 'es_CL', 'es_PE', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_AR': ['es_ES', 'es_MX', 'es_UY', 'es_CL', 'es_CO', 'es_PE', 'es_VE', 'es_EC', 'es_PY', 'es_BO', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_CO': ['es_ES', 'es_MX', 'es_AR', 'es_VE', 'es_EC', 'es_PE', 'es_CL', 'es_UY', 'es_PY', 'es_BO', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_CL': ['es_ES', 'es_MX', 'es_AR', 'es_PE', 'es_CO', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_PE': ['es_ES', 'es_MX', 'es_AR', 'es_CO', 'es_CL', 'es_EC', 'es_BO', 'es_VE', 'es_UY', 'es_PY', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_VE': ['es_ES', 'es_MX', 'es_AR', 'es_CO', 'es_CL', 'es_PE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_EC': ['es_ES', 'es_MX', 'es_AR', 'es_CO', 'es_PE', 'es_CL', 'es_VE', 'es_UY', 'es_PY', 'es_BO', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_UY': ['es_AR', 'es_ES', 'es_MX', 'es_CL', 'es_CO', 'es_PE', 'es_VE', 'es_EC', 'es_PY', 'es_BO', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_PY': ['es_AR', 'es_ES', 'es_MX', 'es_CO', 'es_CL', 'es_PE', 'es_VE', 'es_EC', 'es_UY', 'es_BO', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_BO': ['es_PE', 'es_ES', 'es_MX', 'es_AR', 'es_CO', 'es_CL', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_CR': ['es_MX', 'es_ES', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_AR', 'es_CO', 'es_CL', 'es_PE', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_PA': ['es_MX', 'es_ES', 'es_CR', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es_AR', 'es_CO', 'es_CL', 'es_PE', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_GT': ['es_MX', 'es_ES', 'es_CR', 'es_PA', 'es_HN', 'es_SV', 'es_NI', 'es_AR', 'es_CO', 'es_CL', 'es_PE', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_HN': ['es_MX', 'es_ES', 'es_CR', 'es_PA', 'es_GT', 'es_SV', 'es_NI', 'es_AR', 'es_CO', 'es_CL', 'es_PE', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_SV': ['es_MX', 'es_ES', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_NI', 'es_AR', 'es_CO', 'es_CL', 'es_PE', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_NI': ['es_MX', 'es_ES', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_AR', 'es_CO', 'es_CL', 'es_PE', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_DO', 'es_CU', 'es_PR', 'es'],
        'es_DO': ['es_MX', 'es_ES', 'es_CU', 'es_PR', 'es_AR', 'es_CO', 'es_CL', 'es_PE', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es'],
        'es_CU': ['es_MX', 'es_ES', 'es_DO', 'es_PR', 'es_AR', 'es_CO', 'es_CL', 'es_PE', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es'],
        'es_PR': ['es_MX', 'es_ES', 'es_DO', 'es_CU', 'es_AR', 'es_CO', 'es_CL', 'es_PE', 'es_VE', 'es_EC', 'es_UY', 'es_PY', 'es_BO', 'es_CR', 'es_PA', 'es_GT', 'es_HN', 'es_SV', 'es_NI', 'es'],

        # Portuguese variants
        'pt_BR': ['pt_PT', 'pt'],
        'pt_PT': ['pt_BR', 'pt'],

        # French variants
        'fr_FR': ['fr_CA', 'fr_BE', 'fr_CH', 'fr_LU', 'fr'],
        'fr_CA': ['fr_FR', 'fr_BE', 'fr_CH', 'fr_LU', 'fr'],
        'fr_BE': ['fr_FR', 'fr_CA', 'fr_CH', 'fr_LU', 'fr'],
        'fr_CH': ['fr_FR', 'fr_CA', 'fr_BE', 'fr_LU', 'fr'],
        'fr_LU': ['fr_FR', 'fr_CA', 'fr_BE', 'fr_CH', 'fr'],

        # German variants
        'de_DE': ['de_AT', 'de_CH', 'de_LU', 'de'],
        'de_AT': ['de_DE', 'de_CH', 'de_LU', 'de'],
        'de_CH': ['de_DE', 'de_AT', 'de_LU', 'de'],
        'de_LU': ['de_DE', 'de_AT', 'de_CH', 'de'],

        # Chinese variants
        'zh_CN': ['zh_TW', 'zh_HK', 'zh_SG', 'zh'],
        'zh_TW': ['zh_CN', 'zh_HK', 'zh_SG', 'zh'],
        'zh_HK': ['zh_TW', 'zh_CN', 'zh_SG', 'zh'],
        'zh_SG': ['zh_CN', 'zh_TW', 'zh_HK', 'zh'],

        # Italian variants
        'it_IT': ['it_CH', 'it'],
        'it_CH': ['it_IT', 'it'],

        # Dutch variants
        'nl_NL': ['nl_BE', 'nl'],
        'nl_BE': ['nl_NL', 'nl'],

        # Arabic variants
        'ar_SA': ['ar_EG', 'ar_AE', 'ar_MA', 'ar_DZ', 'ar_TN', 'ar_LB', 'ar_JO', 'ar_SY', 'ar_IQ', 'ar_KW', 'ar_QA', 'ar_BH', 'ar_OM', 'ar_YE', 'ar_LY', 'ar_SD', 'ar'],
        'ar_EG': ['ar_SA', 'ar_AE', 'ar_MA', 'ar_DZ', 'ar_TN', 'ar_LB', 'ar_JO', 'ar_SY', 'ar_IQ', 'ar_KW', 'ar_QA', 'ar_BH', 'ar_OM', 'ar_YE', 'ar_LY', 'ar_SD', 'ar'],
        'ar_AE': ['ar_SA', 'ar_EG', 'ar_MA', 'ar_DZ', 'ar_TN', 'ar_LB', 'ar_JO', 'ar_SY', 'ar_IQ', 'ar_KW', 'ar_QA', 'ar_BH', 'ar_OM', 'ar_YE', 'ar_LY', 'ar_SD', 'ar'],
        'ar_MA': ['ar_SA', 'ar_EG', 'ar_AE', 'ar_DZ', 'ar_TN', 'ar_LB', 'ar_JO', 'ar_SY', 'ar_IQ', 'ar_KW', 'ar_QA', 'ar_BH', 'ar_OM', 'ar_YE', 'ar_LY', 'ar_SD', 'ar'],

        # Russian variants
        'ru_RU': ['ru_BY', 'ru_KZ', 'ru_KG', 'ru_UA', 'ru'],
        'ru_BY': ['ru_RU', 'ru_KZ', 'ru_KG', 'ru_UA', 'ru'],
        'ru_KZ': ['ru_RU', 'ru_BY', 'ru_KG', 'ru_UA', 'ru'],
        'ru_KG': ['ru_RU', 'ru_BY', 'ru_KZ', 'ru_UA', 'ru'],
        'ru_UA': ['ru_RU', 'ru_BY', 'ru_KZ', 'ru_KG', 'ru'],

        # Japanese variants
        'ja_JP': ['ja'],

        # Korean variants
        'ko_KR': ['ko'],

        # Hindi and Indian languages
        'hi_IN': ['hi'],
        'ta_IN': ['ta'],
        'te_IN': ['te'],
        'bn_IN': ['bn_BD', 'bn'],
        'bn_BD': ['bn_IN', 'bn'],
        'gu_IN': ['gu'],
        'mr_IN': ['mr'],
        'kn_IN': ['kn'],
        'ml_IN': ['ml'],
        'pa_IN': ['pa_PK', 'pa'],
        'pa_PK': ['pa_IN', 'pa'],
        'ur_PK': ['ur_IN', 'ur'],
        'ur_IN': ['ur_PK', 'ur'],

        # Vietnamese variants
        'vi_VN': ['vi'],

        # Thai variants
        'th_TH': ['th'],

        # Turkish variants
        'tr_TR': ['tr'],

        # Polish variants
        'pl_PL': ['pl'],

        # Swedish variants
        'sv_SE': ['sv_FI', 'sv'],
        'sv_FI': ['sv_SE', 'sv'],

        # Norwegian variants
        'no_NO': ['nb_NO', 'nn_NO', 'no'],
        'nb_NO': ['no_NO', 'nn_NO', 'no'],
        'nn_NO': ['no_NO', 'nb_NO', 'no'],

        # Danish variants
        'da_DK': ['da'],

        # Finnish variants
        'fi_FI': ['fi'],

        # Greek variants
        'el_GR': ['el_CY', 'el'],
        'el_CY': ['el_GR', 'el'],

        # Hebrew variants
        'he_IL': ['he'],

        # Persian variants
        'fa_IR': ['fa_AF', 'fa'],
        'fa_AF': ['fa_IR', 'fa'],

        # Indonesian/Malay variants
        'id_ID': ['ms_MY', 'ms_BN', 'id'],
        'ms_MY': ['id_ID', 'ms_BN', 'ms'],
        'ms_BN': ['ms_MY', 'id_ID', 'ms'],

        # Czech/Slovak variants
        'cs_CZ': ['sk_SK', 'cs'],
        'sk_SK': ['cs_CZ', 'sk'],

        # Croatian/Serbian/Bosnian variants
        'hr_HR': ['sr_RS', 'bs_BA', 'hr'],
        'sr_RS': ['hr_HR', 'bs_BA', 'sr'],
        'bs_BA': ['hr_HR', 'sr_RS', 'bs'],

        # Ukrainian variants
        'uk_UA': ['uk'],

        # Hungarian variants
        'hu_HU': ['hu'],

        # Romanian variants
        'ro_RO': ['ro_MD', 'ro'],
        'ro_MD': ['ro_RO', 'ro'],

        # Bulgarian variants
        'bg_BG': ['bg'],

        # Lithuanian variants
        'lt_LT': ['lv_LV', 'et_EE', 'lt'],
        'lv_LV': ['lt_LT', 'et_EE', 'lv'],
        'et_EE': ['lt_LT', 'lv_LV', 'et'],

        # Slovenian variants
        'sl_SI': ['sl'],

        # African languages
        'af_ZA': ['af'],
        'sw_KE': ['sw_TZ', 'sw'],
        'sw_TZ': ['sw_KE', 'sw'],
    }

    matched_languages = []

    for requested in requested_languages:
        # First try exact match
        if requested in available_locales:
            matched_languages.append(requested)
            logger.info(f"✅ Exact match found: {requested}")
            continue

        # Check if it's a base language code (e.g., 'en', 'es', 'fr')
        if requested in base_language_groups:
            # Find any variant of this base language
            base_variants = base_language_groups[requested]
            found_base_match = False

            for variant in base_variants:
                if variant in available_locales:
                    matched_languages.append(variant)
                    found_base_match = True
                    break

            if found_base_match:
                continue

        # Try fallback languages (for specific variants like en_US → en_GB)
        fallbacks = language_fallbacks.get(requested, [])
        found_fallback = False

        for fallback in fallbacks:
            if fallback in available_locales:
                matched_languages.append(fallback)
                found_fallback = True
                break

        if not found_fallback:
            logger.warning(f"❌ No match found for: {requested}")

    return matched_languages

def download_captions(captions, download_folder_path, title_of_output_mp4, captions_list, convert_to_srt, portal_name="www"):
    # Find best matching languages
    matched_languages = find_best_language_match(captions, captions_list)

    if not matched_languages:
        available_locales = [cap.get('locale_id', 'unknown') for cap in captions]
        logger.warning(f"⚠️  No captions found for requested languages: {captions_list}")
        logger.info(f"💡 Available languages: {', '.join(available_locales)}")
        return

    # Filter captions based on matched languages
    filtered_captions = [caption for caption in captions if caption["locale_id"] in matched_languages]

    for caption in filtered_captions:
        try:
            response = requests.get(caption['url'])
            response.raise_for_status()

            if caption['file_name'].endswith('.vtt'):
                caption_name = f"{title_of_output_mp4} - {caption['video_label']}.vtt"
                vtt_path = os.path.join(download_folder_path, caption_name)

                with open(vtt_path, 'wb') as file:
                    file.write(response.content)

                if convert_to_srt:
                    srt_name = caption_name.replace('.vtt', '.srt')
                    srt_path = os.path.join(download_folder_path, srt_name)
                    srt_content = webvtt.read(vtt_path)
                    srt_content.save_as_srt(srt_path)

                    # Remove VTT file
                    os.remove(vtt_path)

            else:
                logger.warning(f"⚠️  Unsupported caption format: {caption['file_name']}")
                logger.warning("Only VTT captions are supported. Please create a github issue if you'd like to add support for other formats.")

        except Exception as e:
            logger.error(f"❌ Failed to download caption {caption.get('locale_id', 'unknown')}: {e}")
