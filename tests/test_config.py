import coherence.config as config


def test_normalize_openrouter_settings():
    provider, model, endpoint = config._normalize_llm_settings(
        "openrouter",
        "google/gemini-2.5-flash-lite",
        "",
    )

    assert provider == "openai"
    assert model == "openrouter/google/gemini-2.5-flash-lite"
    assert endpoint == "https://openrouter.ai/api/v1"
