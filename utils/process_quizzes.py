import os
import json
from pathvalidate import sanitize_filename
from constants import QUIZ_URL, logger

def download_quiz(udemy, quiz_id, folder_path, title_of_output_quiz, task_id, progress, portal_name="www", quiz_order=None):
    """Download and process a quiz from Udemy"""
    progress.update(task_id, description=f"Downloading Quiz {title_of_output_quiz}", completed=0)
    
    # Format quiz filename
    if quiz_order is not None:
        quiz_filename = f"Quiz {quiz_order} - {sanitize_filename(title_of_output_quiz)}.html"
    else:
        quiz_filename = f"{title_of_output_quiz}.html"

    # Check if file already exists
    output_path = os.path.join(folder_path, quiz_filename)
    if os.path.exists(output_path):
        progress.update(task_id, completed=100)
        progress.console.log(f"[yellow]Already exists {quiz_filename}[/yellow] ⚠")
        progress.remove_task(task_id)
        return

    # Log the quiz URL we're accessing for debugging
    quiz_url = QUIZ_URL.format(portal_name=portal_name, quiz_id=quiz_id)
    logger.debug(f"Requesting quiz URL: {quiz_url}")
    
    quiz_response = udemy.request(quiz_url).json()
    
    # Log the raw response for debugging
    logger.debug(f"Quiz response: {json.dumps(quiz_response, indent=2)}")
    
    quiz_results = quiz_response.get('results', [])
    
    if not quiz_results:
        progress.console.log(f"[yellow]No quiz data found for {title_of_output_quiz}[/yellow]")
        progress.remove_task(task_id)
        return
    
    # Check if it's a coding assignment or regular quiz
    is_coding_assignment = False
    if len(quiz_results) == 1 and quiz_results[0].get('assessment_type') == 'coding-problem':
        is_coding_assignment = True
    
    # Get the template path
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    os.makedirs(template_dir, exist_ok=True)
    
    template_path = os.path.join(template_dir, 
                               "coding_assignment_template.html" if is_coding_assignment else "quiz_template.html")
    
    if not os.path.exists(template_path):
        logger.error(f"Quiz template not found at {template_path}")
        progress.console.log(f"[red]Quiz template not found. Creating default template.[/red]")
        
        # Create a default template if missing
        if is_coding_assignment:
            with open(template_path, "w", encoding="utf-8") as f:
                f.write("""<!DOCTYPE html>
<html><head><title>Coding Assignment</title></head>
<body><h1>__data_placeholder__</h1></body></html>""")
        else:
            with open(template_path, "w", encoding="utf-8") as f:
                f.write("""<!DOCTYPE html>
<html><head><title>Quiz</title></head>
<body><h1>__data_placeholder__</h1></body></html>""")
    
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html_template = f.read()
            
        if is_coding_assignment:
            # Process coding assignment
            assignment = quiz_results[0]
            prompt = assignment.get('prompt', {})
            
            quiz_data = {
                "title": title_of_output_quiz,
                "hasInstructions": bool(prompt.get('instructions')),
                "hasTests": bool(prompt.get('test_files')),
                "hasSolutions": bool(prompt.get('solution_files')),
                "instructions": prompt.get('instructions', '(None)'),
                "tests": prompt.get('test_files', []),
                "solutions": prompt.get('solution_files', [])
            }
        else:
            # Process regular quiz
            quiz_data = {
                "quiz_id": quiz_id,
                "quiz_description": "",  # This may need to be fetched separately
                "quiz_title": title_of_output_quiz,
                "pass_percent": 80,  # Default pass percentage
                "questions": quiz_results
            }
        
        html_content = html_template.replace("__data_placeholder__", json.dumps(quiz_data))

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        progress.console.log(f"[green]Downloaded {quiz_filename}[/green] ✓")
        
    except Exception as e:
        logger.error(f"Error processing quiz: {str(e)}")
        progress.console.log(f"[red]Error processing quiz {title_of_output_quiz}: {str(e)}[/red]")
    
    progress.update(task_id, completed=100) 
