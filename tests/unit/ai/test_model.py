from company.ai import (
    AIModelRegistry,
    AIRequest,
    DeterministicAIModel,
)


def test_ai_request_defaults():
    request = AIRequest(prompt="hello")

    assert request.prompt == "hello"
    assert request.temperature == 0.0
    assert request.system_prompt is None


def test_deterministic_model_generates_response():
    model = DeterministicAIModel(response="generated")

    response = model.generate(
        AIRequest(prompt="build a project")
    )

    assert response.content == "generated"
    assert response.model == "deterministic"
    assert response.provider == "local"
    assert len(model.requests) == 1


def test_model_registry_registers_and_resolves():
    registry = AIModelRegistry()
    model = DeterministicAIModel()

    registry.register("default", model)

    assert registry.has("default")
    assert registry.get("default") is model
    assert registry.names() == ("default",)


def test_model_registry_rejects_unknown_model():
    registry = AIModelRegistry()

    try:
        registry.get("missing")
    except KeyError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("Expected KeyError")
