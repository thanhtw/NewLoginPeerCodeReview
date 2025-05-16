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


# Regeneration Prompt Template
regeneration_template = """ You are an educational Java error creator who deliberately introduces specific errors in code for teaching purposes.
Task: Modify this Java code to contain exactly {total_requested} errors - no more, no less.
The code must only contain the specific errors requested below.
Original code domain: {domain}
Missing errors - deliberately add these errors (do not fix or resolve them):
{missing_text}
Existing errors to preserve - do not modify these errors:
{found_text}
Very important instructions:

Focus on implementing exactly the requested errors
Never add comments like "// added to fix", "// fixed", or "// corrected" - these errors are meant to stay as errors!
Do not change the domain or structure of the code
Errors must be actual Java errors, not just comments about errors
Use exactly the same {domain} domain and maintain the original code structure
For each error you add, include a comment in this format: // ERROR: [type] - [name] - [brief description]
Do not try to improve or fix the code - it should contain deliberate errors for educational purposes
The entire purpose is to create flawed code for students to learn to identify problems

Verification steps before submission:

Count the total number of errors in the code, confirm it is exactly {total_requested}
Verify each missing error from the list has now been implemented
Confirm all existing errors that should be preserved still exist and are unchanged
Ensure any extra errors have been removed

Provide two versions of the code:

1. First, provide the ANNOTATED VERSION with error comments:
```java-annotated
// Your code with error annotations
```

2. Then, provide the CLEAN VERSION without any error comments:
```java-clean
// The same code with the same errors but no error annotations
```
Original code:
```java
{code}
```
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
"Identified Problems": [
    {{
    "Error Type": "Logical",
    "Error Name": "Misunderstanding of short-circuit evaluation",
    "Line Number": 42,
    "Code Segment": "if (obj != null & obj.getValue() > 0) { ... }",
    "Expanation": "This code uses the non-short-circuit '&' operator instead of '&&', which means obj.getValue() will be evaluated even if obj is null, potentially causing a NullPointerException."
    }}
    // List all implemented errors that match the requested list
],
"Missed Problems": [
    {{
    "Error Type":"Code Quality", 
    "Error Name": "Code duplication",
    "Expanation": "The code does not contain instances of duplicated logic or repeated code blocks that could be refactored into shared methods. Code duplication is when similar functionality is implemented multiple times instead of being extracted into reusable methods, which reduces maintainability and increases the risk of inconsistent bug fixes."
    }}
    // List all requested errors that aren't implemented
],
"Valid": true,  // Set to true ONLY if ALL requested errors are implemented, no more and no fewer
"Feedback": "The code successfully implements all {error_count} requested errors."  // Provide brief overall assessment
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
EVALUATION THRESHOLDS:
1. Meaningfulness threshold: {meaningful_score_threshold} (how well the explanation describes WHY it's a problem)
2. Accuracy threshold: {accuracy_score_threshold} (how correctly the issue and location are identified)

ANALYSIS INSTRUCTIONS:
1. Carefully read both the code and the student's review
2. For EACH known issue, determine if the student addressed it
3. Score each student comment that addresses a known issue
    + Accuracy (0.0-1.0): How correctly the student identified the issue and its location
    + Meaningfulness (0.0-1.0): How well the student explained WHY it's a problem
4. CRITICAL SORTING RULE: An issue is only "Identified" if BOTH scores meet or exceed thresholds
    + If Accuracy >= {accuracy_score_threshold} AND Meaningfulness >= {meaningful_score_threshold} → Add to "Identified Problems"
    + Otherwise → Add to "Missed Problems" (even if partially addressed with insufficient scores)
5. Count ONLY the properly identified issues (meeting both thresholds) in "Identified Count"

RESPONSE REQUIREMENTS:
Provide your analysis in JSON format with these components:

```json
{{
"Identified Problems": [
    {{
    "Problem": "SPECIFIC KNOWN ISSUE TEXT",
    "Student Comment": "STUDENT'S RELEVANT COMMENT",
    "Accuracy": 0.9,
    "Meaningfulness": 0.8,
    "Feedback": "Brief feedback on this identification"
    }}
],
"Missed Problems": [
    {{
    "Problem": "SPECIFIC KNOWN ISSUE TEXT - Not addressed at all",
    "hint": "A helpful educational hint for finding this issue"
    }},
    {{
    "Problem": "SPECIFIC KNOWN ISSUE TEXT - Addressed but scores too low",
    "Student Comment": "STUDENT'S RELEVANT COMMENT",
    "Accuracy": 0.5,
    "Meaningfulness": 0.3,
    "hint": "Comment lacks sufficient detail about why this is problematic"
    }}
],
"Identified Count": 1,
"Total Problems": {problem_count},
"Identified Percentage": 25.0,
"Review Sufficient": false,
"Feedback": "Overall assessment with specific improvement suggestions"
}}
```

CRITICAL REQUIREMENTS:
1. Include each problem EXACTLY ONCE in EITHER "Identified Problems" OR "Missed Problems"
2. DO NOT create any additional fields other than those shown above
3. Only include a problem in "Identified Problems" if BOTH scores meet the thresholds
4. Include original student comments when available, even for missed problems
5. Calculate "Identified Count" as the COUNT of items in "Identified Problems"
6. For items in "Missed Problems" that were addressed by the student but with insufficient scores, include the actual scores
"""

# Feedback Prompt Template
feedback_template = """As a Java mentor providing targeted code review guidance, create concise feedback for a student.

CONTEXT:
- Student completed review attempt {iteration} of {max_iterations}
- Found {identified}/{total} issues ({accuracy:.1f}%)
- {remaining} review attempts remaining

REVIEW QUALITY ISSUES:
- Some identified issues lack meaningful comments
- A meaningful comment must explain WHAT the issue is and WHY it's problematic

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
5. Include an example of how to turn a vague comment into a meaningful one

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

CORRECTLY IDENTIFIED ISSUES:
{identified_text}

MISSED ISSUES:
{missed_text}


{progress_info}

REPORT REQUIREMENTS:
1. Create a comprehensive educational report in markdown format
2. Include these sections:
- Performance Summary (with metrics and overall assessment)
- Correctly Identified Issues (with praise for what they found correctly)
- Missed Issues (with educational explanations of why they matter)
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