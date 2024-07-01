# This is a representation of the data dictionary

# Eventually, it should contain every column for every table, organized by editbox

DATADICT = {
    'biography': {
        'milestones': {
            'primary': 'MILESTONE_CLASS',
            'columns': [
                "MILESTONE_DETAIL",
                "MILESTONE_Q",
                "MILESTONE_GEOID",
                "MILESTONE_GEOIDQ",
                "MILESTONE_BD",
                "MILESTONE_BDQ",
                "MILESTONE_ED",
                "MILESTONE_EDQ",
                "MILESTONE_BASIS"
            ],
            'default': 'BIOGRAPHY*MILESTONE'
        },
    },
    'ms_ed': {
        'milestones': {
            'primary': 'MILESTONE_CLASS',
            'columns': [
                "MILESTONE_DETAIL",
                "MILESTONE_MAKER_IDP",
                "MILESTONE_MAKER_ID",
                "MILESTONE_MAKER_IDQ",
                "MILESTONE_MAKERBASIS",
                "MILESTONE_FUNDER_IDP",
                "MILESTONE_FUNDER_ID",
                "MILESTONE_FUNDER_IDQ",
                "MILESTONE_FUNDERBASIS",
                "MILESTONE_GEOID",
                "MILESTONE_GEOIDQ",
                "MILESTONE_GEOBASIS",
                "MILESTONE_BD",
                "MILESTONE_BDQ",
                "MILESTONE_ED",
                "MILESTONE_EDQ",
                "MILESTONE_BASIS"
            ],
            'default': 'MS_ED*MILESTONE'
        },
    },
    'uniform_title': {
        'milestones': {
            'primary': 'MILESTONE_CLASS',
            'columns': [
                "MILESTONE_DETAIL",
                "MILESTONE_GEOID",
                "MILESTONE_GEOIDQ",
                "MILESTONE_GEOBASIS",
                "MILESTONE_BD",
                "MILESTONE_BDQ",
                "MILESTONE_ED",
                "MILESTONE_EDQ",
                "MILESTONE_BASIS"
            ],
            'default': 'UNIFORM_TITLE*MILESTONE'
        }
    }
}
