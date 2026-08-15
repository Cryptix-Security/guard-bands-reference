from guardbands import GuardBandCrypto
from integrations.rag_middleware import (
    RetrievedDocument,
    build_guarded_rag_prompt,
    document_context,
    wrap_retrieved_documents,
)


def test_wrap_retrieved_documents_uses_per_document_context():
    crypto = GuardBandCrypto(b"test-secret")
    base_context = {
        "request_id": "req-001",
        "tenant_id": "tenant-a",
        "user": "alice",
        "policy_path": "rag.read_only",
    }
    documents = [
        RetrievedDocument("Doc one", "kb://one", {"chunk": 1}),
        RetrievedDocument("Doc two", "kb://two", {"chunk": 2}),
    ]

    wrapped_documents = wrap_retrieved_documents(documents, base_context, crypto)

    assert len(wrapped_documents) == 2
    assert wrapped_documents[0]["context"]["document_index"] == 0
    assert wrapped_documents[1]["context"]["document_index"] == 1

    first_result = crypto.extract_and_verify(
        wrapped_documents[0]["wrapped_content"],
        document_context(base_context, documents[0], 0),
    )
    second_result = crypto.extract_and_verify(
        wrapped_documents[1]["wrapped_content"],
        document_context(base_context, documents[1], 1),
    )

    assert first_result["valid"] is True
    assert first_result["content"] == "Doc one"
    assert second_result["valid"] is True
    assert second_result["content"] == "Doc two"


def test_build_guarded_rag_prompt_includes_wrapped_documents():
    crypto = GuardBandCrypto(b"test-secret")
    documents = [
        RetrievedDocument("Doc text", "kb://one"),
    ]
    wrapped_documents = wrap_retrieved_documents(
        documents,
        {"request_id": "req-001"},
        crypto,
    )

    prompt = build_guarded_rag_prompt("What happened?", wrapped_documents)

    assert "Question: What happened?" in prompt
    assert "Document 1 (kb://one):" in prompt
    assert "⟪INERT:START:v:1:" in prompt
