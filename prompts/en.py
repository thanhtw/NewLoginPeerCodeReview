"""
English prompt templates for Java Peer Review Training System.

This module contains all the English language prompt templates used for LLM interactions.
"""

# Code Generation Prompt Template
code_generation_template = """You are an expert Java programming instructor creating educational code with specific deliberate errors for students to practice code review skills.

MAIN TASK:
Generate a {code_length} Java program for a {domain_str} system that contains EXACTLY {error_count} intentional errors for a code review exercise.

CODE STRUCTURE REQUIREMENTS:
- Create {complexity}
- Make the code realistic, well-structured, and appropriate for a {domain_str} application
- Follow standard Java conventions for all correct parts of the code
- The code should look professional except for the deliberate errors

{difficulty_instructions}

ERROR IMPLEMENTATION REQUIREMENTS:
- Implement EXACTLY {error_count} errors - this is CRITICAL (no more, no fewer)
- Only implement the SPECIFIC errors listed below
- Each error must be an actual Java error, not just a comment
- In the annotated version, mark each error with a comment: // ERROR: [TYPE] - [NAME] - [Brief explanation]
- NEVER add comments like "// added to fix" or "// this is incorrect" - the errors are meant to remain as errors!
- Ensure errors are findable through code review (not just runtime errors)

EXACTLY {error_count} ERRORS TO IMPLEMENT:

{error_instructions}

VERIFICATION CHECKLIST (COMPLETE BEFORE SUBMITTING):
- [ ] Code follows the {code_length}/{difficulty_level} complexity requirements
- [ ] Code is realistic and appropriate for a {domain_str} application
- [ ] EXACTLY {error_count} errors are implemented (no more, no fewer)
- [ ] Each implemented error matches one from the requested list
- [ ] All errors are marked with appropriate comments in the annotated version
- [ ] The clean version has the same errors but without the comments
- [ ] Both versions would compile (except for deliberate compilation errors)

OUTPUT FORMAT:
1. First, provide the ANNOTATED VERSION with error comments:
```java-annotated
// Your code with error annotations
```

2. Then, provide the CLEAN VERSION without any error comments:
```java-clean
// The same code with the same errors but no error annotations
```

IMPORTANT: Verify you have implemented EXACTLY {error_count} errors before completing.
"""

# Difficulty level templates
beginner_instructions = """
BEGINNER-FRIENDLY CODE REQUIREMENTS:
- Use very descriptive variable/method names (studentName, calculateTotal)
- Keep methods short (3-10 lines each) and focused on a single task
- Use basic control structures (if/else, simple loops) with clear conditions
- Include helpful comments explaining the code's purpose
- Avoid complex nested structures or advanced Java features
- Make errors relatively obvious for educational purposes
- Implement errors in a way that beginners can reasonably identify them
"""

intermediate_instructions = """
INTERMEDIATE-LEVEL CODE REQUIREMENTS:
- Use a mix of simple and moderately complex code structures
- Include a variety of control structures and data types
- Keep methods reasonably sized (5-15 lines)
- Implement some errors that require careful reading to identify
- Add appropriate documentation where needed
- Create realistic code that might appear in a small application
- Balance obvious errors with some more subtle ones
"""

advanced_instructions = """
ADVANCED-LEVEL CODE REQUIREMENTS:
- Create more sophisticated code structures with appropriate complexity
- Implement errors that might be hidden in logical flow or edge cases
- Use a variety of Java features and design patterns when appropriate
- Challenge the student to think deeply about the code
- Include subtle errors that require careful analysis to identify
- Create realistic code that follows good structure despite the errors
- Implement errors that interact with each other in non-obvious ways
"""

# Evaluation Prompt Template
evaluation_template = """As a Java code quality expert, your task is to analyze Java code to determine if it correctly implements specific requested errors.

MAIN TASK:
Evaluate if the provided Java code correctly implements EXACTLY {error_count} specific errors that were requested.

CODE TO EVALUATE:
```java
{code}
```

THE {error_count} SPECIFIC ERRORS THAT SHOULD BE PRESENT:
{error_instructions}

EVALUATION INSTRUCTIONS:
1. Examine the code line by line, identifying each error that matches the requested list
2. For each error you find, note:
- The specific error type and name
- The exact line number(s) where it appears
- A brief code segment showing the error
- A concise explanation of why it matches the requested error
3. Check if any requested errors are missing from the code
4. For valid implementation, the code must contain EXACTLY {error_count} errors - no more, no fewer

RESPONSE FORMAT:
Your evaluation must be returned in this JSON format:

```json
{{
"found_errors": [
    {{
    "error_type": "BUILD",  
    "error_name": "NullPointerException",
    "line_number": 42,
    "code_segment": "String str = null; int length = str.length();",
    "explanation": "This code will cause a NullPointerException because it calls length() on a null String"
    }}
    // List all implemented errors that match the requested list
],
"missing_errors": [
    {{
    "error_type": "CHECKSTYLE",
    "error_name": "MemberName",
    "explanation": "The code doesn't contain any variable names that violate member naming conventions"
    }}
    // List all requested errors that aren't implemented
],
"valid": true,  // Set to true ONLY if ALL requested errors are implemented, no more and no fewer
"feedback": "The code successfully implements all {error_count} requested errors."  // Provide brief overall assessment
}}
```

VERIFICATION CHECKLIST:
- Confirm that each found error truly matches the corresponding requested error
- Verify that the total count of found errors is EXACTLY {error_count} for validity
- Double-check any errors you believe are missing to ensure they're truly absent
- Ensure your JSON response is properly formatted for processing

IMPORTANT: Focus solely on the specified error types and names, not general code quality issues.
"""

# Review Analysis Prompt Template
review_analysis_template = """You are an educational assessment specialist analyzing a student's Java code review skills.

MAIN TASK:
Analyze the student's code review against a set of known issues to evaluate their code review effectiveness.

CODE BEING REVIEWED:
```java
{code}
```

{problem_count} KNOWN ISSUES IN THE CODE:
{problems_text}

STUDENT'S REVIEW SUBMISSION:
```
{student_review}
```

ANALYSIS INSTRUCTIONS:
1. Carefully read both the code and the student's review
2. Identify which of the known issues the student correctly found
3. Note which known issues the student missed
4. Identify any false positives (things the student flagged as issues that aren't actual problems)
5. Evaluate the review quality (accuracy, completeness, clarity, and specificity)
6. Determine if the review is sufficient (>= 60% of issues correctly identified)

RESPONSE REQUIREMENTS:
Provide your analysis in JSON format with these components:

```json
{
"identified_problems": [
    {
    "problem": "SPECIFIC KNOWN ISSUE TEXT",
    "student_comment": "STUDENT'S RELEVANT COMMENT",
    "accuracy": 0.9,
    "feedback": "Brief feedback on this identification"
    }
    // Include all correctly identified issues
],
"missed_problems": [
    {
    "problem": "SPECIFIC KNOWN ISSUE TEXT",
    "hint": "A helpful educational hint for finding this type of issue"
    }
    // Include all missed issues
],
"false_positives": [
    {
    "student_comment": "STUDENT'S INCORRECT COMMENT",
    "explanation": "Why this isn't actually an issue"
    }
    // Include any incorrect identifications
],
"identified_count": 3,  // Number of correctly identified issues
"total_problems": {problem_count},  // Total number of known issues
"identified_percentage": 60.0,  // Percentage of issues correctly identified
"review_quality_score": 7.5,  // Score from 1-10 rating review quality
"review_sufficient": true,  // true if >= 60% of issues identified
"feedback": "Overall assessment with specific improvement suggestions"
}
```

EVALUATION CRITERIA:
- For matching student comments to known issues, look for:
- Correct identification of the issue type
- Accurate location (line number or description)
- Understanding of why it's a problem
- Consider partial credit if they identified an issue but misunderstood it
- A review is sufficient if the student correctly identified at least 60% of known issues

TIPS FOR ANALYSIS:
- Be thorough in examining every part of the student's review
- Be generous in matching student comments to issues if they show understanding
- Provide educational feedback that helps the student improve their code review skills
- If the student uses different terminology but correctly identifies an issue, count it as correct
"""

# Feedback Prompt Template
feedback_template = """As a Java mentor providing targeted code review guidance, create concise feedback for a student.

CONTEXT:
- Student completed review attempt {iteration} of {max_iterations}
- Found {identified}/{total} issues ({accuracy:.1f}%)
- {remaining} review attempts remaining

CORRECTLY IDENTIFIED ISSUES:
{identified_text}

MISSED ISSUES:
{missed_text}

TASK:
Create brief, specific guidance (3-4 sentences max) to help the student find more issues in their next review attempt.

GUIDANCE REQUIREMENTS:
1. Be extremely concise and focused (max 3-4 short sentences)
2. Target the most important 1-2 areas for improvement
3. Provide specific, actionable strategies (what to look for)
4. Be encouraging but direct
5. Focus only on helping them find missed issues, not general code review skills

EXAMPLE GOOD GUIDANCE:
"Look more carefully at method parameters and return types. Several issues involve type mismatches that can be spotted by comparing declared types with actual values. Also check for proper null handling before method calls."

EXAMPLE POOR GUIDANCE (too general):
"Keep trying to find more issues. There are several problems in the code that you missed. Try to be more thorough in your next review attempt."

RESPONSE FORMAT:
Provide ONLY the guidance text with no introduction or explanation.
"""

# Comparison Report Prompt Template
comparison_report_template = """You are an educational assessment expert creating a detailed, informative code review feedback report for a Java programming student.

CONTEXT:
The student has conducted a code review exercise, identifying errors in a Java code snippet. Your task is to create a comprehensive, educational report on their performance.

PERFORMANCE METRICS:
- Total issues in the code: {total_problems}
- Issues correctly identified: {identified_count} ({accuracy:.1f}%)
- Issues missed: {len_missed_str}
- False positives (things incorrectly flagged as issues): {len_false_str}

CORRECTLY IDENTIFIED ISSUES:
{identified_text}

MISSED ISSUES:
{missed_text}

FALSE POSITIVES:
{false_positive_text}

{progress_info}

REPORT REQUIREMENTS:
1. Create a comprehensive educational report in markdown format
2. Include these sections:
- Performance Summary (with metrics and overall assessment)
- Correctly Identified Issues (with praise for what they found correctly)
- Missed Issues (with educational explanations of why they matter)
- False Positives (if any, with explanations of why these aren't actual issues)
- Progress Analysis (if multiple attempts, analyzing their improvement)
- Tips for Improvement (specific, actionable advice based on their performance)

3. Be educational and constructive, not just evaluative
4. Use a warm, encouraging tone while maintaining honesty about areas for improvement
5. Focus on helping them become a better code reviewer, not just scoring this attempt
6. Highlight patterns in what they missed or found to help them improve systematically
7. Include specific Java code review tips relevant to their performance
8. Make the report visually readable with appropriate markdown formatting

IMPORTANT FORMATTING:
- Use markdown for clear organization (headers, bullet points, etc.)
- Format code snippets in markdown code blocks if referring to specific code
- Use bold or italic text for emphasis where appropriate
- Keep paragraphs reasonably short for readability
"""