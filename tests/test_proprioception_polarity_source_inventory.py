from neurofly.proprioception_polarity_source_inventory import parse_manifest


def test_manifest_extracts_exact_frozen_targets_and_fanc_candidates():
    payload = {
        "status": "OK",
        "data": {
            "id": 123,
            "persistentUrl": "https://doi.org/10.7910/DVN/7WTH1N",
            "latestVersion": {
                "versionNumber": 1,
                "versionMinorNumber": 0,
                "versionState": "RELEASED",
                "releaseTime": "2026-01-01T00:00:00Z",
                "files": [
                    {
                        "directoryLabel": "compiled_data/banc_888",
                        "dataFile": {
                            "id": 10,
                            "filename": "banc_888_meta.feather",
                            "filesize": 100,
                            "checksum": {"type": "MD5", "value": "abc"},
                            "restricted": False,
                        },
                    },
                    {
                        "directoryLabel": "nblast",
                        "dataFile": {
                            "id": 11,
                            "filename": "banc_fanc_1116_nblast.feather",
                            "filesize": 200,
                            "checksum": {"type": "MD5", "value": "def"},
                            "restricted": False,
                        },
                    },
                    {
                        "directoryLabel": "metadata",
                        "dataFile": {
                            "id": 12,
                            "filename": "fanc_meta.csv",
                            "filesize": 300,
                            "checksum": {"type": "MD5", "value": "ghi"},
                            "restricted": False,
                        },
                    },
                    {"dataFile": {"id": 99, "filename": "unrelated.txt", "filesize": 1}},
                ],
            },
        },
    }
    report = parse_manifest(payload)
    assert report["total_files"] == 4
    assert len(report["relevant_files"]) == 3
    assert report["exact_targets"]["banc_888_meta.feather"][0]["file_id"] == 10
    assert report["exact_targets"]["banc_fanc_1116_nblast.feather"][0]["file_id"] == 11
    assert report["exact_targets"]["fanc_meta.csv"][0]["file_id"] == 12
    assert len(report["manifest_sha256"]) == 64
