from carelens.config import Settings
from carelens.samples import load_sample_case, sample_manifest


def test_manifest_and_all_sample_files_are_loadable():
    settings = Settings(openai_api_key="test")
    manifest = sample_manifest()
    assert {"case_a", "case_b", "case_c"} <= set(manifest["cases"])
    for case_id in manifest["cases"]:
        documents = load_sample_case(case_id, settings)
        assert documents
        assert all(document.filename for document in documents)

