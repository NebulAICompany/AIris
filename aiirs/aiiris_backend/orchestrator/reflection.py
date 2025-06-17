from agents import Agent, Runner
from typing import Callable


async def reflect_and_retry(
    prompt: str, initial_answer: str, agent: Agent, max_retries: int = 2
) -> str:
    current_answer = initial_answer
    retry_count = 0

    while retry_count < max_retries:
        reflection_prompt = f"""
        Evaluate the following question and answer pair:

        Question: {prompt}
        
        Answer: {current_answer}
        
        Please evaluate the answer based on these criteria:
        1. Completeness: Does it fully address all aspects of the question?
        2. Accuracy: Is the information correct and well-supported by sources?
        3. Clarity: Is the reasoning process clear and well-structured?
        4. Source Attribution: Are all sources properly cited?
        
        Provide your evaluation in this format:
        Completeness: [Score 1-5]
        Accuracy: [Score 1-5]
        Clarity: [Score 1-5]
        Source Attribution: [Score 1-5]
        Overall Assessment: [Pass/Fail]
        Improvement Suggestions: [List specific areas for improvement]
        """

        # Use the agent for reflection
        reflection_result = await Runner.run(agent, reflection_prompt)
        reflection = reflection_result.final_output

        # Check if the answer needs improvement
        if "Overall Assessment: Fail" in reflection:
            retry_count += 1
            if retry_count < max_retries:
                # Create an enhanced prompt with the reflection feedback
                enhanced_prompt = f"""
                Previous Answer: {current_answer}
                
                Evaluation Feedback: {reflection}
                
                Please provide an improved answer addressing the feedback above.
                """
                # Get improved answer using the agent
                result = await Runner.run(agent, enhanced_prompt)
                current_answer = result.final_output
        else:
            return current_answer

    return current_answer
