import pytest
from knowledge_splitter import split_documents

@pytest.mark.parametrize('text', ['   ', '\t\n', '\u3000'])
def test_whitespace_only_documents_are_skipped(text):
    docs = [{'source': 'blank.md', 'text': text}]
    assert split_documents(docs, chunk_size=4) == []
    assert docs[0]['text'] == text

def test_nonblank_content_is_preserved():
    assert split_documents([{'source':'a.md','text':' a '}], 4)[0]['text'] == ' a '
