"""
Unified AI Model service for ThesisAI Tool.

This module provides a unified interface for different AI providers.
"""

import asyncio
import json
import aiohttp
import requests
from typing import List, Optional, AsyncGenerator, Dict, Any
from fastapi import HTTPException

from config.config import config
from file_processing.text_extractor import extract_text_from_file
from ai.providers.ai_provider import AIProvider

class UnifiedAIModel:
    """Unified interface for different AI providers"""
    
    def __init__(self):
        self.config = config
        self.seed = config.AI_SEED
        self.provider_config = config.get_ai_provider_config()

    def get_api_key(self, provider: AIProvider) -> Optional[str]:
        """Get API key for the specified provider"""
        provider_name = provider.value
        return self.provider_config.get(provider_name, {}).get('api_key')

    def get_model(self, provider: AIProvider, model: Optional[str] = None) -> str:
        """Get the model to use for the specified provider"""
        if model:
            return model
        provider_name = provider.value
        return self.provider_config.get(provider_name, {}).get('default_model', 'gpt-4o')

    def get_headers(self, provider: AIProvider) -> Dict[str, str]:
        """Get headers for the specified provider"""
        api_key = self.get_api_key(provider)
        if not api_key:
            raise HTTPException(status_code=500, detail=f"No API key configured for {provider}")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Add provider-specific headers
        if provider == AIProvider.OPENROUTER:
            headers.update({
                "HTTP-Referer": "http://localhost",
                "X-Title": "ThesisAI"
            })
        
        return headers

    def get_api_url(self, provider: AIProvider) -> str:
        """Get API URL for the specified provider"""
        provider_name = provider.value
        return self.provider_config.get(provider_name, {}).get('api_url', '')

    async def make_request(self, provider: AIProvider, messages: List[Dict[str, str]], 
                          model: Optional[str] = None, stream: bool = False) -> Dict[str, Any]:
        """Make a request to the specified AI provider"""
        api_key = self.get_api_key(provider)
        if not api_key:
            raise HTTPException(status_code=500, detail=f"No API key configured for {provider}")
        
        model_name = self.get_model(provider, model)
        headers = self.get_headers(provider)
        api_url = self.get_api_url(provider)
        
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
        }
        
        # Add provider-specific parameters
        if provider == AIProvider.OPENROUTER:
            payload["seed"] = self.seed
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error with {provider}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error with {provider}: {str(e)}")

    async def make_streaming_request(self, provider: AIProvider, messages: List[Dict[str, str]], 
                                   model: Optional[str] = None, pacing_delay: float = 0.01) -> AsyncGenerator[str, None]:
        """Make a streaming request to the specified AI provider with improved UX"""
        api_key = self.get_api_key(provider)
        if not api_key:
            print(f"🔄 Using fallback mode for {provider} - no API key available")
            yield f"data: {json.dumps({'type': 'status', 'content': f'[FALLBACK MODE] {provider.value.upper()} Analysis'})}\n\n"
            yield f"data: {json.dumps({'type': 'content', 'content': f'This is a simulated response since no API key is configured for {provider}.'})}\n\n"
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            return

        model_name = self.get_model(provider, model)
        headers = self.get_headers(provider)
        api_url = self.get_api_url(provider)
        
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,
        }
        
        # Add provider-specific parameters
        if provider == AIProvider.OPENROUTER:
            payload["seed"] = self.seed
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"❌ Error with {provider}: {error_text}")
                        yield f"data: {json.dumps({'type': 'error', 'content': f'Error with {provider}: {error_text}'})}\n\n"
                        return
                    
                    # Send initial status
                    yield f"data: {json.dumps({'type': 'status', 'content': f'{provider.value.upper()} Analysis Started'})}\n\n"
                    
                    buffer = ""
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            if data == '[DONE]':
                                break
                            
                            try:
                                json_data = json.loads(data)
                                if 'choices' in json_data and len(json_data['choices']) > 0:
                                    delta = json_data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        content = delta['content']
                                        buffer += content
                                        
                                        # Send content in chunks for better UX
                                        if len(buffer) >= 10 or '\n' in buffer:
                                            yield f"data: {json.dumps({'type': 'content', 'content': buffer})}\n\n"
                                            buffer = ""
                                            await asyncio.sleep(pacing_delay)
                            except json.JSONDecodeError:
                                continue
                    
                    # Send any remaining buffer
                    if buffer:
                        yield f"data: {json.dumps({'type': 'content', 'content': buffer})}\n\n"
                    
                    yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                    
        except Exception as e:
            print(f"❌ Error with {provider}: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error with {provider}: {str(e)}'})}\n\n"

    async def analyze_thesis_stream(self, file_path: str, custom_instructions: str, 
                                  predefined_questions: List[str], provider: AIProvider = None, 
                                  model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Analyze thesis with streaming response"""
        if not provider:
            provider = AIProvider(config.get_active_provider())
        
        try:
            # Extract text from file
            text_content = extract_text_from_file(file_path)
            
            # Prepare the analysis prompt
            analysis_prompt = f"""
You are an expert thesis evaluator. Please analyze the following thesis document and provide comprehensive feedback.

CUSTOM INSTRUCTIONS:
{custom_instructions}

PREDEFINED QUESTIONS TO ADDRESS:
{chr(10).join([f"{i+1}. {question}" for i, question in enumerate(predefined_questions)])}

THESIS CONTENT:
{text_content[:8000]}  # Limit content for API constraints

Please provide a detailed analysis covering:
1. Overall assessment
2. Strengths and weaknesses
3. Specific feedback on each predefined question
4. Recommendations for improvement
5. Grading on different aspects

Format your response in a clear, structured manner with sections and bullet points.
"""
            
            messages = [
                {"role": "system", "content": "You are an expert thesis evaluator with deep knowledge of academic writing, research methodology, and evaluation criteria."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            async for chunk in self.make_streaming_request(provider, messages, model):
                yield chunk
                
        except Exception as e:
            print(f"❌ Error in thesis analysis: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error in thesis analysis: {str(e)}'})}\n\n"

    async def grade_formatting_style(self, file_path: str, provider: AIProvider = None, 
                                   model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Grade formatting and style aspects"""
        if not provider:
            provider = AIProvider(config.get_active_provider())
        
        try:
            text_content = extract_text_from_file(file_path)
            
            grading_prompt = f"""
You are an expert thesis evaluator. Please grade the FORMATTING AND STYLE aspects of this thesis.

GRADING CRITERIA:
- Document structure and organization
- Formatting consistency (fonts, spacing, margins)
- Professional presentation
- Clarity and readability
- Proper use of headings and sections
- Citation and reference formatting

THESIS CONTENT:
{text_content[:6000]}

Please provide:
1. A grade (A-F) with justification
2. Specific feedback on formatting strengths and weaknesses
3. Detailed recommendations for improvement
4. Overall assessment of presentation quality

Format your response with clear sections and bullet points.
"""
            
            messages = [
                {"role": "system", "content": "You are an expert thesis evaluator specializing in formatting and style assessment."},
                {"role": "user", "content": grading_prompt}
            ]
            
            async for chunk in self.make_streaming_request(provider, messages, model):
                yield chunk
                
        except Exception as e:
            print(f"❌ Error in formatting grading: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error in formatting grading: {str(e)}'})}\n\n"

    async def grade_purpose_objectives(self, file_path: str, provider: AIProvider = None, 
                                     model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Grade purpose and objectives"""
        if not provider:
            provider = AIProvider(config.get_active_provider())
        
        try:
            text_content = extract_text_from_file(file_path)
            
            grading_prompt = f"""
You are an expert thesis evaluator. Please grade the PURPOSE AND OBJECTIVES aspects of this thesis.

GRADING CRITERIA:
- Clarity of research purpose
- Well-defined objectives
- Logical connection between purpose and objectives
- Feasibility of objectives
- Alignment with academic standards
- Practical relevance

THESIS CONTENT:
{text_content[:6000]}

Please provide:
1. A grade (A-F) with justification
2. Assessment of purpose clarity and grounding
3. Evaluation of objective definition and feasibility
4. Specific recommendations for improvement
5. Overall assessment of purpose-objective alignment

Format your response with clear sections and bullet points.
"""
            
            messages = [
                {"role": "system", "content": "You are an expert thesis evaluator specializing in purpose and objectives assessment."},
                {"role": "user", "content": grading_prompt}
            ]
            
            async for chunk in self.make_streaming_request(provider, messages, model):
                yield chunk
                
        except Exception as e:
            print(f"❌ Error in purpose grading: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error in purpose grading: {str(e)}'})}\n\n"

    async def grade_theoretical_foundation(self, file_path: str, provider: AIProvider = None, 
                                         model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Grade theoretical foundation"""
        if not provider:
            provider = AIProvider(config.get_active_provider())
        
        try:
            text_content = extract_text_from_file(file_path)
            
            grading_prompt = f"""
You are an expert thesis evaluator. Please grade the THEORETICAL FOUNDATION aspects of this thesis.

GRADING CRITERIA:
- Depth of theoretical framework
- Critical analysis of existing literature
- Appropriate use of theoretical concepts
- Logical theoretical progression
- Integration of theory with research
- Academic rigor in theoretical discussion

THESIS CONTENT:
{text_content[:6000]}

Please provide:
1. A grade (A-F) with justification
2. Assessment of theoretical framework depth
3. Evaluation of critical thinking and analysis
4. Specific recommendations for improvement
5. Overall assessment of theoretical foundation

Format your response with clear sections and bullet points.
"""
            
            messages = [
                {"role": "system", "content": "You are an expert thesis evaluator specializing in theoretical foundation assessment."},
                {"role": "user", "content": grading_prompt}
            ]
            
            async for chunk in self.make_streaming_request(provider, messages, model):
                yield chunk
                
        except Exception as e:
            print(f"❌ Error in theoretical foundation grading: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error in theoretical foundation grading: {str(e)}'})}\n\n"

    async def grade_professional_connection(self, file_path: str, provider: AIProvider = None, 
                                          model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Grade professional connection and relevance"""
        if not provider:
            provider = AIProvider(config.get_active_provider())
        
        try:
            text_content = extract_text_from_file(file_path)
            
            grading_prompt = f"""
You are an expert thesis evaluator. Please grade the PROFESSIONAL CONNECTION aspects of this thesis.

GRADING CRITERIA:
- Relevance to professional field
- Connection to working life
- Practical applicability
- Industry relevance
- Professional development value
- Real-world impact potential

THESIS CONTENT:
{text_content[:6000]}

Please provide:
1. A grade (A-F) with justification
2. Assessment of professional relevance
3. Evaluation of practical applicability
4. Specific recommendations for improvement
5. Overall assessment of professional connection

Format your response with clear sections and bullet points.
"""
            
            messages = [
                {"role": "system", "content": "You are an expert thesis evaluator specializing in professional connection assessment."},
                {"role": "user", "content": grading_prompt}
            ]
            
            async for chunk in self.make_streaming_request(provider, messages, model):
                yield chunk
                
        except Exception as e:
            print(f"❌ Error in professional connection grading: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error in professional connection grading: {str(e)}'})}\n\n"

    async def grade_development_task(self, file_path: str, provider: AIProvider = None, 
                                   model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Grade development/research task definition"""
        if not provider:
            provider = AIProvider(config.get_active_provider())
        
        try:
            text_content = extract_text_from_file(file_path)
            
            grading_prompt = f"""
You are an expert thesis evaluator. Please grade the DEVELOPMENT/RESEARCH TASK aspects of this thesis.

GRADING CRITERIA:
- Clarity of research/development task
- Justification of task selection
- Feasibility of task completion
- Methodological approach
- Task definition quality
- Research question formulation

THESIS CONTENT:
{text_content[:6000]}

Please provide:
1. A grade (A-F) with justification
2. Assessment of task clarity and definition
3. Evaluation of task justification and feasibility
4. Specific recommendations for improvement
5. Overall assessment of development task quality

Format your response with clear sections and bullet points.
"""
            
            messages = [
                {"role": "system", "content": "You are an expert thesis evaluator specializing in development task assessment."},
                {"role": "user", "content": grading_prompt}
            ]
            
            async for chunk in self.make_streaming_request(provider, messages, model):
                yield chunk
                
        except Exception as e:
            print(f"❌ Error in development task grading: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error in development task grading: {str(e)}'})}\n\n"

    async def grade_conclusions_proposals(self, file_path: str, provider: AIProvider = None, 
                                        model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Grade conclusions and development proposals"""
        if not provider:
            provider = AIProvider(config.get_active_provider())
        
        try:
            text_content = extract_text_from_file(file_path)
            
            grading_prompt = f"""
You are an expert thesis evaluator. Please grade the CONCLUSIONS AND DEVELOPMENT PROPOSALS aspects of this thesis.

GRADING CRITERIA:
- Quality of conclusions drawn
- Evidence-based conclusions
- Development proposal quality
- Practical implementation suggestions
- Future research directions
- Overall synthesis quality

THESIS CONTENT:
{text_content[:6000]}

Please provide:
1. A grade (A-F) with justification
2. Assessment of conclusion quality
3. Evaluation of development proposals
4. Specific recommendations for improvement
5. Overall assessment of conclusions and proposals

Format your response with clear sections and bullet points.
"""
            
            messages = [
                {"role": "system", "content": "You are an expert thesis evaluator specializing in conclusions and proposals assessment."},
                {"role": "user", "content": grading_prompt}
            ]
            
            async for chunk in self.make_streaming_request(provider, messages, model):
                yield chunk
                
        except Exception as e:
            print(f"❌ Error in conclusions grading: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error in conclusions grading: {str(e)}'})}\n\n"

    async def grade_material_methodology(self, file_path: str, provider: AIProvider = None, 
                                       model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Grade material and methodological choices"""
        if not provider:
            provider = AIProvider(config.get_active_provider())
        
        try:
            text_content = extract_text_from_file(file_path)
            
            grading_prompt = f"""
You are an expert thesis evaluator. Please grade the MATERIAL AND METHODOLOGICAL CHOICES aspects of this thesis.

GRADING CRITERIA:
- Diversity of materials used
- Appropriateness of methodology
- Methodological foundation
- Data collection methods
- Analysis approach quality
- Research design effectiveness

THESIS CONTENT:
{text_content[:6000]}

Please provide:
1. A grade (A-F) with justification
2. Assessment of material diversity and foundation
3. Evaluation of methodological choices
4. Specific recommendations for improvement
5. Overall assessment of materials and methodology

Format your response with clear sections and bullet points.
"""
            
            messages = [
                {"role": "system", "content": "You are an expert thesis evaluator specializing in materials and methodology assessment."},
                {"role": "user", "content": grading_prompt}
            ]
            
            async for chunk in self.make_streaming_request(provider, messages, model):
                yield chunk
                
        except Exception as e:
            print(f"❌ Error in material methodology grading: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error in material methodology grading: {str(e)}'})}\n\n"

    async def grade_treatment_analysis(self, file_path: str, provider: AIProvider = None, 
                                     model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Grade treatment and analysis of material"""
        if not provider:
            provider = AIProvider(config.get_active_provider())
        
        try:
            text_content = extract_text_from_file(file_path)
            
            grading_prompt = f"""
You are an expert thesis evaluator. Please grade the TREATMENT AND ANALYSIS OF MATERIAL aspects of this thesis.

GRADING CRITERIA:
- Controlled treatment of materials
- Proficient analysis approach
- Systematic data processing
- Analytical depth
- Critical evaluation quality
- Methodological rigor in analysis

THESIS CONTENT:
{text_content[:6000]}

Please provide:
1. A grade (A-F) with justification
2. Assessment of treatment control and proficiency
3. Evaluation of analysis depth and quality
4. Specific recommendations for improvement
5. Overall assessment of treatment and analysis

Format your response with clear sections and bullet points.
"""
            
            messages = [
                {"role": "system", "content": "You are an expert thesis evaluator specializing in treatment and analysis assessment."},
                {"role": "user", "content": grading_prompt}
            ]
            
            async for chunk in self.make_streaming_request(provider, messages, model):
                yield chunk
                
        except Exception as e:
            print(f"❌ Error in treatment analysis grading: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error in treatment analysis grading: {str(e)}'})}\n\n"

    async def grade_results_product(self, file_path: str, provider: AIProvider = None, 
                                  model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Grade results and product quality"""
        if not provider:
            provider = AIProvider(config.get_active_provider())
        
        try:
            text_content = extract_text_from_file(file_path)
            
            grading_prompt = f"""
You are an expert thesis evaluator. Please grade the RESULTS AND PRODUCT aspects of this thesis.

GRADING CRITERIA:
- Originality of results
- Application value of results
- Product quality and completeness
- Innovation level
- Practical implementation
- Impact and significance

THESIS CONTENT:
{text_content[:6000]}

Please provide:
1. A grade (A-F) with justification
2. Assessment of result originality and application
3. Evaluation of product quality and completeness
4. Specific recommendations for improvement
5. Overall assessment of results and product

Format your response with clear sections and bullet points.
"""
            
            messages = [
                {"role": "system", "content": "You are an expert thesis evaluator specializing in results and product assessment."},
                {"role": "user", "content": grading_prompt}
            ]
            
            async for chunk in self.make_streaming_request(provider, messages, model):
                yield chunk
                
        except Exception as e:
            print(f"❌ Error in results product grading: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error in results product grading: {str(e)}'})}\n\n" 