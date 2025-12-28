"""
Personality Extractor Agent
Extracts personality traits from character descriptions using NLP and LLM
"""

import logging
import re
from typing import List, Dict, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt
from utils.retry import after_func
from utils.async_wrapper import run_in_thread


class PersonalityTraits(BaseModel):
    """Structured personality traits output"""
    traits: List[str] = Field(description="List of personality traits (3-5 traits)")
    dominant_trait: str = Field(description="The most dominant personality trait")
    description: str = Field(description="Brief personality summary")


class PersonalityExtractor:
    """
    Agent for extracting personality traits from character descriptions
    Uses LLM to analyze text and extract meaningful personality characteristics
    """
    
    # Common personality trait keywords for quick extraction
    TRAIT_KEYWORDS = {
        # Positive traits
        "勇敢": ["勇敢", "勇气", "无畏", "大胆", "英勇"],
        "善良": ["善良", "仁慈", "温柔", "体贴", "关怀"],
        "聪明": ["聪明", "智慧", "机智", "睿智", "明智"],
        "乐观": ["乐观", "开朗", "积极", "阳光", "快乐"],
        "坚强": ["坚强", "坚韧", "顽强", "不屈", "刚毅"],
        "诚实": ["诚实", "真诚", "坦率", "正直", "可靠"],
        "幽默": ["幽默", "风趣", "诙谐", "搞笑", "有趣"],
        "自信": ["自信", "自豪", "骄傲", "果断", "坚定"],
        "冷静": ["冷静", "沉着", "镇定", "理智", "从容"],
        "热情": ["热情", "热心", "激情", "活力", "充满活力"],
        
        # Negative/Complex traits
        "傲慢": ["傲慢", "自大", "骄傲", "高傲", "自负"],
        "冷漠": ["冷漠", "冷酷", "无情", "冷血", "麻木"],
        "胆小": ["胆小", "懦弱", "怯懦", "畏惧", "害怕"],
        "固执": ["固执", "倔强", "顽固", "执拗", "死板"],
        "狡猾": ["狡猾", "狡诈", "奸诈", "诡计多端"],
        "冲动": ["冲动", "鲁莽", "急躁", "暴躁", "易怒"],
        "神秘": ["神秘", "神秘莫测", "深不可测", "难以捉摸"],
        "忧郁": ["忧郁", "忧伤", "悲伤", "沮丧", "消沉"],
    }
    
    def __init__(
        self,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize personality extractor
        
        Args:
            llm_model: LLM model name (optional, for advanced extraction)
            llm_provider: LLM provider (optional)
            api_key: API key for LLM (optional)
        """
        self.llm = None
        if llm_model and llm_provider:
            try:
                self.llm = init_chat_model(
                    model=llm_model,
                    model_provider=llm_provider,
                    api_key=api_key
                )
            except Exception as e:
                logging.warning(f"Failed to initialize LLM for personality extraction: {e}")
                logging.info("Will use keyword-based extraction as fallback")
    
    @run_in_thread
    def extract_traits_simple(
        self,
        description: str,
        max_traits: int = 5
    ) -> List[str]:
        """
        Extract personality traits using keyword matching
        Fast but less accurate method (now async-compatible)
        
        Args:
            description: Character description text
            max_traits: Maximum number of traits to extract
        
        Returns:
            List of personality traits
        """
        found_traits = []
        description_lower = description.lower()
        
        # Check each trait category
        for trait, keywords in self.TRAIT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in description_lower:
                    if trait not in found_traits:
                        found_traits.append(trait)
                    break
            
            if len(found_traits) >= max_traits:
                break
        
        # If no traits found, return default
        if not found_traits:
            found_traits = ["待定"]
        
        return found_traits[:max_traits]
    
    @retry(stop=stop_after_attempt(3), after=after_func, reraise=True)
    async def extract_traits_advanced(
        self,
        description: str,
        appearance: str = "",
        max_traits: int = 5
    ) -> PersonalityTraits:
        """
        Extract personality traits using LLM analysis
        More accurate but slower method
        
        Args:
            description: Character description text
            appearance: Character appearance description
            max_traits: Maximum number of traits to extract
        
        Returns:
            PersonalityTraits object with extracted traits
        """
        if not self.llm:
            # Fallback to simple extraction
            traits = self.extract_traits_simple(description, max_traits)
            return PersonalityTraits(
                traits=traits,
                dominant_trait=traits[0] if traits else "待定",
                description=f"基于描述提取的性格特征"
            )
        
        # Prepare parser
        parser = PydanticOutputParser(pydantic_object=PersonalityTraits)
        
        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的角色分析专家。请从给定的角色描述中提取3-5个最突出的性格特征。

要求：
1. 性格特征应该简洁明了（2-4个字）
2. 选择最能代表角色的特征
3. 避免重复或相似的特征
4. 提供一个简短的性格总结

{format_instructions}"""),
            ("human", """请分析以下角色并提取性格特征：

角色描述：{description}

外貌特征：{appearance}

请提取该角色的主要性格特征。""")
        ])
        
        # Format prompt
        formatted_prompt = prompt.format_messages(
            description=description,
            appearance=appearance or "未提供",
            format_instructions=parser.get_format_instructions()
        )
        
        try:
            # Call LLM
            response = await self.llm.ainvoke(formatted_prompt)
            
            # Parse response
            personality = parser.parse(response.content)
            
            # Limit traits
            if len(personality.traits) > max_traits:
                personality.traits = personality.traits[:max_traits]
            
            return personality
            
        except Exception as e:
            logging.error(f"LLM personality extraction failed: {e}")
            # Fallback to simple extraction
            traits = self.extract_traits_simple(description, max_traits)
            return PersonalityTraits(
                traits=traits,
                dominant_trait=traits[0] if traits else "待定",
                description=f"基于关键词提取的性格特征"
            )
    
    @run_in_thread
    def extract_from_dialogue(
        self,
        dialogue: str,
        max_traits: int = 3
    ) -> List[str]:
        """
        Extract personality traits from character dialogue (now async-compatible)
        
        Args:
            dialogue: Character's dialogue text
            max_traits: Maximum number of traits to extract
        
        Returns:
            List of personality traits inferred from dialogue
        """
        traits = []
        dialogue_lower = dialogue.lower()
        
        # Analyze dialogue patterns
        if any(word in dialogue_lower for word in ["哈哈", "呵呵", "笑", "开心"]):
            traits.append("幽默")
        
        if any(word in dialogue_lower for word in ["一定", "必须", "绝对", "肯定"]):
            traits.append("坚定")
        
        if any(word in dialogue_lower for word in ["也许", "可能", "大概", "或许"]):
            traits.append("谨慎")
        
        if any(word in dialogue_lower for word in ["！", "?!", "..."]):
            if "！" in dialogue:
                traits.append("热情")
            if "..." in dialogue:
                traits.append("深思")
        
        # Check for formal vs casual language
        if any(word in dialogue_lower for word in ["您", "敬请", "恭"]):
            traits.append("礼貌")
        
        return traits[:max_traits] if traits else ["待定"]
    
    @run_in_thread
    def enhance_personality_description(
        self,
        traits: List[str],
        description: str
    ) -> str:
        """
        Create an enhanced personality description combining traits and original description (now async-compatible)
        
        Args:
            traits: List of personality traits
            description: Original character description
        
        Returns:
            Enhanced personality description
        """
        if not traits or traits == ["待定"]:
            return description
        
        traits_str = "、".join(traits)
        enhanced = f"性格特征：{traits_str}。{description}"
        
        return enhanced