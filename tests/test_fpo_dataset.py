from fpo.service import FPOService

def test_fpo_dataset_loaded_min_count():
    svc = FPOService()
    # Ensure external JSON loaded
    assert svc.json_source_loaded() is True, "Expected external fpo_data.json to be loaded"
    assert svc.total_fpos() >= 2000, f"Unexpected low FPO count: {svc.total_fpos()}"
