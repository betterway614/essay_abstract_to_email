import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)

class LLMProcessor:
    def __init__(self):
        if not settings or not settings.llm_config.get("enable"):
            self.client = None
            logger.info("LLM Processor is disabled or config missing.")
            return

        self._base_url = settings.llm_base_url
        self._alt_base_url = self._derive_alt_base_url(self._base_url)
        self._tried_alt_base_url = False
        self._disabled = False

        self.client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=self._base_url)

        env_model = os.getenv("LLM_MODEL", "").strip()
        self.model = env_model or settings.llm_config.get("model", "gpt-3.5-turbo")
        self.language = settings.llm_config.get("language", "zh-CN")
        self.semaphore = asyncio.Semaphore(5)

    async def summarize_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary for a single paper.
        Returns the paper dict enriched with 'ai_summary' field.
        """
        if not self.client or self._disabled:
            paper["ai_summary"] = None
            return paper

        # If summary already exists (e.g. from cache? not implementing cache yet), return.
        
        prompt = self._build_prompt(paper)
        
        try:
            async with self.semaphore:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful research assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    timeout=30
                )
                
                content = response.choices[0].message.content
                paper["ai_summary"] = content
                logger.info(f"Successfully summarized: {paper['title'][:30]}...")
                
        except Exception as e:
            if self._is_model_not_exist_error(e):
                if self._alt_base_url and not self._tried_alt_base_url:
                    self._tried_alt_base_url = True
                    logger.warning(f"LLM model error detected; retrying with base_url={self._alt_base_url}")
                    try:
                        self.client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=self._alt_base_url)
                        async with self.semaphore:
                            response = await self.client.chat.completions.create(
                                model=self.model,
                                messages=[
                                    {"role": "system", "content": "You are a helpful research assistant."},
                                    {"role": "user", "content": prompt}
                                ],
                                temperature=0.3,
                                timeout=30
                            )
                        content = response.choices[0].message.content
                        paper["ai_summary"] = content
                        return paper
                    except Exception as e2:
                        logger.error(f"LLM retry failed: {type(e2).__name__}: {e2}")

                self._disabled = True
                logger.error("LLM disabled due to model configuration error. Check LLM_MODEL/model and LLM_BASE_URL.")
                paper["ai_summary"] = None
                return paper

            logger.error(f"Failed to summarize paper '{paper['title'][:30]}...': {e}")
            paper["ai_summary"] = None # Fallback to None (template handles this)

        return paper

    def _build_prompt(self, paper: Dict[str, Any]) -> str:
        return f"""你是严谨的论文解读助手。请仅基于标题与摘要，不要编造不存在的实验结果、数据、方法细节或结论；不确定请明确写“摘要未提供/不确定”。输出语言：{self.language}。

输出要求：
- 只输出纯文本，不要使用代码块。
- 总长度控制在 180~260 字左右，尽量信息密度高。
- 按固定结构输出，每一行以字段名开头，字段名保持一致。

请按以下结构输出（每项一行）：
【一句话总结】…
【背景/痛点】…
【核心方法】…（尽量用“输入→处理→输出”的方式表述）
【主要贡献】…（1~3 点，逗号分隔）
【结论/效果】…（没有量化指标就写“摘要未给出量化结果”）
【局限与风险】…（至少 1 点）
【适用场景】…（1~2 个）
【关键词】…（3~6 个，用逗号分隔）

论文标题：{paper['title']}
论文摘要：{paper['summary']}"""

    async def process_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a list of papers concurrently.
        """
        if not self.client:
            return papers

        tasks = [self.summarize_paper(paper) for paper in papers]
        return await asyncio.gather(*tasks)

    def _derive_alt_base_url(self, base_url: str) -> Optional[str]:
        if not base_url:
            return None
        normalized = base_url.rstrip("/")
        if normalized.endswith("/v1"):
            return normalized[:-3]
        return None

    def _is_model_not_exist_error(self, err: Exception) -> bool:
        msg = str(err).lower()
        return "model not exist" in msg or "model_not_found" in msg or "model_not_exist" in msg

if __name__ == "__main__":
    # Test stub
    pass
