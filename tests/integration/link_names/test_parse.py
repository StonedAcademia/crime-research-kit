from tests.integration.link_names.helpers import load_tcr


def test_parse_name_entries_supports_aliases_and_files(tmp_path):
    tcr = load_tcr()
    names_file = tmp_path / "names.txt"
    names_file.write_text(
        "\n".join(
            [
                "# ignored",
                "Demo Leader|Leader",
                "Demo Witness|Witness",
                "Demo Leader|Leader",
            ]
        ),
        encoding="utf-8",
    )

    entries = tcr.parse_name_entries(["Inline Person|I.P."], [str(names_file)])

    assert [entry["primary"] for entry in entries] == ["Demo Leader", "Demo Witness", "Inline Person"]
    assert entries[0]["aliases"] == ["Demo Leader", "Leader"]
    assert entries[2]["aliases"] == ["Inline Person", "I.P."]


def test_parse_name_entries_merges_overlapping_aliases(tmp_path):
    tcr = load_tcr()
    names_file = tmp_path / "names.txt"
    names_file.write_text(
        "\n".join(
            [
                "Demo Leader|Leader",
                "Leader|D. Leader",
                "Demo Witness|Witness",
            ]
        ),
        encoding="utf-8",
    )

    entries = tcr.parse_name_entries(["Witness|D. Witness"], [str(names_file)])

    assert [entry["primary"] for entry in entries] == ["Demo Leader", "Demo Witness"]
    assert entries[0]["aliases"] == ["Demo Leader", "Leader", "D. Leader"]
    assert entries[1]["aliases"] == ["Demo Witness", "Witness", "D. Witness"]
