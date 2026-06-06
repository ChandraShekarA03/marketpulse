from app.rag.chunking import chunk_text


def test_chunk_text_splits_long_text_into_chunks():
    text = "This is sentence one. " * 50 + "This is the final sentence."
    chunks = chunk_text(text, chunk_size=300, overlap=50)

    assert len(chunks) > 1
    assert all(len(chunk) <= 300 for chunk in chunks)
    assert any("This is the final sentence." in chunk for chunk in chunks)


def test_chunk_text_removes_html_tags():
    raw = "<html><body><h1>Title</h1><p>First paragraph.</p><p>Second paragraph.</p></body></html>"
    chunks = chunk_text(raw, chunk_size=200, overlap=20)

    assert len(chunks) == 1
    assert "Title" in chunks[0]
    assert "First paragraph." in chunks[0]
    assert "Second paragraph." in chunks[0]
