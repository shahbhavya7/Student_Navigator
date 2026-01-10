"""Prompt templates for content generation using LangChain."""

from langchain_core.prompts import ChatPromptTemplate


# Lesson Generation Template
LESSON_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert educational content creator specializing in adaptive learning. 
Create clear, engaging lessons tailored to student needs. Your content should be well-structured, 
pedagogically sound, and appropriate for the specified difficulty level."""),
    
    ("human", """Create a comprehensive lesson on the following topic:

**Topic**: {topic}
**Difficulty Level**: {difficulty}
**Target Duration**: {estimated_minutes} minutes
**Prerequisites**: {prerequisites}
**Student Cognitive Load**: {cognitive_load_context}

Please structure the lesson as follows:

1. **Title**: Clear, engaging title
2. **Introduction**: Hook the learner and state learning objectives (2-3 sentences)
3. **Main Content**: 2-4 well-organized sections with:
   - Clear explanations
   - Concrete examples
   - Visual descriptions or analogies
4. **Practice Questions**: 2-3 quick check-for-understanding questions
5. **Summary**: Key takeaways (3-5 bullet points)
6. **Next Steps**: Suggestions for further learning

Return the content as structured markdown. Adjust complexity based on the cognitive load context - 
if cognitive load is high, simplify explanations and add more scaffolding.""")
])


# Quiz Generation Template
QUIZ_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an assessment designer creating fair, educational quizzes that test 
understanding without causing anxiety. Your questions should be clear, have one correct answer, 
and include helpful explanations."""),
    
    ("human", """Create a quiz on the following topic:

**Topic**: {topic}
**Difficulty Level**: {difficulty}
**Number of Questions**: {num_questions}
**Cognitive Load Context**: {cognitive_load_context}

For each question, provide:
- Clear question text
- 4 plausible answer options (labeled A, B, C, D)
- The correct answer (specify the letter)
- A brief explanation of why the answer is correct

Return the quiz as a JSON array with this structure:
```json
[
  {{
    "question": "Question text here",
    "options": {{
      "A": "First option",
      "B": "Second option",
      "C": "Third option",
      "D": "Fourth option"
    }},
    "correct_answer": "B",
    "explanation": "Explanation of correct answer"
  }}
]
```

Adjust question complexity based on cognitive load - if high, make questions more straightforward.""")
])


# Exercise Generation Template
EXERCISE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a practice problem designer creating hands-on exercises that reinforce 
learning through application. Your exercises should be practical, clearly stated, and include 
progressive hints to support student learning."""),
    
    ("human", """Create a practice exercise on the following topic:

**Topic**: {topic}
**Difficulty Level**: {difficulty}
**Exercise Type**: {exercise_type}
**Cognitive Load Context**: {cognitive_load_context}

Structure the exercise as follows:

1. **Problem Statement**: Clear description of what the student needs to do
2. **Hints**: 3 progressive hints (from general to specific) to help students who get stuck
3. **Solution**: Complete solution with step-by-step explanation
4. **Extension Challenges**: 1-2 optional harder variations

Return as structured markdown. If cognitive load is high, provide more detailed hints and simpler problems.""")
])


# Recap/Review Template
RECAP_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a review content specialist creating concise, focused review materials 
for students who need additional support. Your recaps should identify common misconceptions and 
provide clear, memorable explanations."""),
    
    ("human", """Create review content for the following:

**Topics to Review**: {weak_topics}
**Recent Errors/Misconceptions**: {recent_errors}
**Cognitive Load**: {cognitive_load_context}

Structure the recap as follows:

1. **Quick Summary**: Essential concepts in 3-5 bullet points
2. **Common Misconceptions**: Address specific errors or confusion points
3. **Key Examples**: 2-3 clear examples that illustrate the concepts
4. **Quick Practice**: 3 simple review questions with answers

Keep it concise and focused. Use simple language and provide extra support given the cognitive load context.""")
])


# Easier Version Template
EASIER_VERSION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an educational content adapter specializing in making complex material 
more accessible. Your goal is to simplify without losing educational value."""),
    
    ("human", """Simplify the following educational content:

**Original Content**:
{original_content}

**Target Difficulty**: easier
**Current Cognitive Load**: {cognitive_load_context}

Create a simpler version by:
- Using simpler vocabulary and shorter sentences
- Breaking complex concepts into smaller chunks
- Adding more examples and analogies
- Providing more scaffolding and step-by-step guidance
- Reducing the amount of information presented at once

Return the simplified content in the same format as the original.""")
])


# Harder Version Template
HARDER_VERSION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an educational content adapter specializing in increasing rigor and 
depth. Your goal is to challenge students appropriately without overwhelming them."""),
    
    ("human", """Increase the difficulty of the following educational content:

**Original Content**:
{original_content}

**Target Difficulty**: harder
**Current Cognitive Load**: {cognitive_load_context}

Create a more challenging version by:
- Introducing advanced concepts and terminology
- Reducing scaffolding and explicit guidance
- Adding complexity and nuance
- Including multi-step reasoning requirements
- Connecting to broader or more abstract ideas

Return the enhanced content in the same format as the original.""")
])


# Alternative Explanation Template
ALTERNATIVE_EXPLANATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an educational content creator skilled in finding multiple ways to 
explain the same concept. Your goal is to provide a fresh perspective that might resonate 
better with different learning styles."""),
    
    ("human", """Create an alternative explanation for the following content:

**Original Content**:
{original_content}

**Variation Strategy**: {variation_strategy}
**Cognitive Load Context**: {cognitive_load_context}

Create a new version that:
- Uses different analogies or metaphors
- Approaches the topic from a different angle
- Appeals to different learning modalities (visual, kinesthetic, etc.)
- Provides fresh examples and applications
- Maintains the same difficulty level but different teaching approach

Return the alternative content in the same format as the original.""")
])


def get_prompt_template(content_type: str) -> ChatPromptTemplate:
    """
    Get the appropriate prompt template for a content type.
    
    Args:
        content_type: Type of content (lesson, quiz, exercise, recap)
    
    Returns:
        ChatPromptTemplate for the specified content type
    """
    templates = {
        'lesson': LESSON_PROMPT,
        'quiz': QUIZ_PROMPT,
        'exercise': EXERCISE_PROMPT,
        'recap': RECAP_PROMPT,
    }
    
    return templates.get(content_type.lower(), LESSON_PROMPT)
