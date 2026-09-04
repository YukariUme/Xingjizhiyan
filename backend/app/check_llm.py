"""DeepSeek / LLM 连通性自检脚本。

用法：先配置 backend/.env，然后：
    python -m app.check_llm
"""

from app.config import get_settings
from app.services.llm.factory import get_llm_service


def main() -> None:
    settings = get_settings()
    print(f"LLM_PROVIDER = {settings.llm_provider}")
    print(f"DEEPSEEK_MODEL = {settings.deepseek_model}")
    print(f"DEEPSEEK_BASE_URL = {settings.deepseek_base_url}")
    if settings.llm_provider == "deepseek" and not settings.deepseek_api_key:
        print("✗ 尚未配置 DEEPSEEK_API_KEY：请在 backend/.env 中填入你的密钥。")
        raise SystemExit(1)
    service = get_llm_service()
    print(f"服务实例：{service.name}")
    reply = service.generate(
        "请用一句话回答：什么是 RAG？",
        system="你是连通性自检助手，回答尽量简短。",
        max_tokens=100,
    )
    print(f"✓ 调用成功，模型回复：\n{reply[:200]}")


if __name__ == "__main__":
    main()

