from typing import NamedTuple, List, Dict, Any

class TestData(NamedTuple):
    """Структура для хранения одного тестового случая колоды."""
    deck_code: str
    character_ids: List[int]
    action_ids: List[int]
    character_names: List[str]
    expected_resonances: List[str]
    mock_api_response: Dict[str, Any]


DECK_TEST_CASES: List[TestData] = [
    # --- СЛУЧАЙ 1: Inazuma резонанс (Кокоми, Яэ) ---
    TestData(
        deck_code="ADDQyv4PBLEQCM4QCxDQC9kQCxGxDLUMDCEBCN4QDNECDPYQDEAA",
        character_ids=[1205, 1408, 1302],
        action_ids=[
            212051, 212051, 213021, 213021, 214081, 311101, 311401, 312201,
            312301, 312401, 321003, 321003, 321006, 322001, 322002, 322007,
            322012, 332001, 332001, 332003, 332004, 332006, 332007, 332008,
            332009, 332010, 332012, 332013, 333005, 333006
        ],
        character_names=["Sangonomiya Kokomi", "Xiangling", "Yae Miko"],
        expected_resonances=["Inazuma"],
        mock_api_response={
            "retcode": 0,
            "message": "OK",
            "data": {
                "role_cards": [
                    {"basic": {"item_id": 1205, "name": "Sangonomiya Kokomi"}},
                    {"basic": {"item_id": 1408, "name": "Yae Miko"}},
                    {"basic": {"item_id": 1302, "name": "Xiangling"}}
                ],
                "action_cards": [
                    {"basic": {"item_id": 212051}}, {"basic": {"item_id": 212051}},
                    {"basic": {"item_id": 213021}}, {"basic": {"item_id": 213021}},
                    {"basic": {"item_id": 214081}}, {"basic": {"item_id": 311101}},
                    {"basic": {"item_id": 311401}}, {"basic": {"item_id": 312201}},
                    {"basic": {"item_id": 312301}}, {"basic": {"item_id": 312401}},
                    {"basic": {"item_id": 321003}}, {"basic": {"item_id": 321003}},
                    {"basic": {"item_id": 321006}}, {"basic": {"item_id": 322001}},
                    {"basic": {"item_id": 322002}}, {"basic": {"item_id": 322007}},
                    {"basic": {"item_id": 322012}}, {"basic": {"item_id": 332001}},
                    {"basic": {"item_id": 332001}}, {"basic": {"item_id": 332003}},
                    {"basic": {"item_id": 332004}}, {"basic": {"item_id": 332006}},
                    {"basic": {"item_id": 332007}}, {"basic": {"item_id": 332008}},
                    {"basic": {"item_id": 332009}}, {"basic": {"item_id": 332010}},
                    {"basic": {"item_id": 332012}}, {"basic": {"item_id": 332013}},
                    {"basic": {"item_id": 333005}}, {"basic": {"item_id": 333006}}
                ]
            }
        }
    ),
    # --- СЛУЧАЙ 2: Geo и Natlan резонансы (Качина, Мавуика) ---
    TestData(
        deck_code="GBDB294OHJDR6Y8OGKDx6s8PHEDw9JcTCbFxO1ccGkGxxKsaC/Fgr8AdDEEB1KEdGsAA",
        character_ids=[1608, 1315, 1610],
        action_ids=[
            216081, 216081, 216101, 216101, 312004, 312004, 312025, 312030,
            312030, 321004, 321014, 321014, 322028, 322028, 330002, 331601,
            331601, 331602, 331602, 332004, 332004, 332025, 332025, 332042,
            332042, 333016, 333016, 333020, 333020, 333027
        ],
        character_names=["Kachina", "Mavuika", "Navia"],
        expected_resonances=["Geo", "Natlan"],
        mock_api_response={
            "retcode": 0,
            "message": "OK",
            "data": {
                "role_cards": [
                    {"basic": {"item_id": 1608, "name": "Navia"}},
                    {"basic": {"item_id": 1315, "name": "Mavuika"}},
                    {"basic": {"item_id": 1610, "name": "Kachina"}}
                ],
                "action_cards": [
                    {"basic": {"item_id": 216081}}, {"basic": {"item_id": 216081}},
                    {"basic": {"item_id": 216101}}, {"basic": {"item_id": 216101}},
                    {"basic": {"item_id": 312004}}, {"basic": {"item_id": 312004}},
                    {"basic": {"item_id": 312025}}, {"basic": {"item_id": 312030}},
                    {"basic": {"item_id": 312030}}, {"basic": {"item_id": 321004}},
                    {"basic": {"item_id": 321014}}, {"basic": {"item_id": 321014}},
                    {"basic": {"item_id": 322028}}, {"basic": {"item_id": 322028}},
                    {"basic": {"item_id": 330002}}, {"basic": {"item_id": 331601}},
                    {"basic": {"item_id": 331601}}, {"basic": {"item_id": 331602}},
                    {"basic": {"item_id": 331602}}, {"basic": {"item_id": 332004}},
                    {"basic": {"item_id": 332004}}, {"basic": {"item_id": 332025}},
                    {"basic": {"item_id": 332025}}, {"basic": {"item_id": 332042}},
                    {"basic": {"item_id": 332042}}, {"basic": {"item_id": 333016}},
                    {"basic": {"item_id": 333016}}, {"basic": {"item_id": 333020}},
                    {"basic": {"item_id": 333020}}, {"basic": {"item_id": 333027}}
                ]
            }
        }
    ),
    # --- СЛУЧАЙ 3: Электро резонанс (Е Лань, Сайно, Клоринда) ---
    TestData(
        deck_code="EZCA2R0NG7DQ5ZcOClBB9DEPE0ERCFcQFYFxO5MTGbEwlsYQDMFgDMoRDAGgENEdDUAA",
        character_ids=[1209, 1404, 1412],
        action_ids=[
            312004, 312017, 312019, 312019, 312025, 312025, 312029, 312029,
            322005, 322005, 322009, 322009, 322016, 323004, 323004, 330002,
            331401, 331401, 332004, 332004, 332024, 332024, 332025, 332025,
            332037, 333004, 333004, 333008, 333008, 333020
        ],
        character_names=["Clorinde", "Cyno", "Yelan"],
        expected_resonances=["Electro"],
        mock_api_response={
            "retcode": 0,
            "message": "OK",
            "data": {
                "role_cards": [
                    {"basic": {"item_id": 1209, "name": "Yelan"}},
                    {"basic": {"item_id": 1404, "name": "Cyno"}},
                    {"basic": {"item_id": 1412, "name": "Clorinde"}}
                ],
                "action_cards": [
                    {"basic": {"item_id": 312004}}, {"basic": {"item_id": 312017}},
                    {"basic": {"item_id": 312019}}, {"basic": {"item_id": 312019}},
                    {"basic": {"item_id": 312025}}, {"basic": {"item_id": 312025}},
                    {"basic": {"item_id": 312029}}, {"basic": {"item_id": 312029}},
                    {"basic": {"item_id": 322005}}, {"basic": {"item_id": 322005}},
                    {"basic": {"item_id": 322009}}, {"basic": {"item_id": 322009}},
                    {"basic": {"item_id": 322016}}, {"basic": {"item_id": 323004}},
                    {"basic": {"item_id": 323004}}, {"basic": {"item_id": 330002}},
                    {"basic": {"item_id": 331401}}, {"basic": {"item_id": 331401}},
                    {"basic": {"item_id": 332004}}, {"basic": {"item_id": 332004}},
                    {"basic": {"item_id": 332024}}, {"basic": {"item_id": 332024}},
                    {"basic": {"item_id": 332025}}, {"basic": {"item_id": 332025}},
                    {"basic": {"item_id": 332037}}, {"basic": {"item_id": 333004}},
                    {"basic": {"item_id": 333004}}, {"basic": {"item_id": 333008}},
                    {"basic": {"item_id": 333008}}, {"basic": {"item_id": 333020}}
                ]
            }
        }
    )
]