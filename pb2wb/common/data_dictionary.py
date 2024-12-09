from common.enums import Table

# This is a representation of the data dictionary

# Eventually, it should contain every column for every table, organized by editbox

DATADICT = {
    Table.ANALYTIC.value: {
        'id_fields': [
            'CNUM',
            'TEXT_MANID',
            'TEXT_UNIID',
            'COMMENT_BIOID',
            'RELATED_BIOID',
            'RELATED_BIBID',
            'RELATED_MANID',
            'RELATED_UNIID',
            'SUBJECT_BIOID',
            'SUBJECT_GEOID',
            'SUBJECT_INSID',
            'SUBJECT_SUBID'
        ],
        'dataclip_fields': [
            'DOCUMENT_LANGUAGE',
            'TEXT_LOCCLASS',
            'INC_EXP_CLASS',
            'VARIANT_NAMECLASS',
            'RELATED_BIOCLASS',
            'RELATED_BIBCLASS',
            'RELATED_MANCLASS',
            'RELATED_UNICLASS',
            'STATUS',
            'INTERNET_CLASS'
        ]
    },
    Table.BIBLIOGRAPHY.value: {
        'id_fields': [
            'BIBID',
            'RELATED_LIBID',
            'RELATED_BIBID',
            'SUBJECT_BIOID',
            'SUBJECT_GEOID',
            'SUBJECT_INSID',
            'SUBJECT_SUBID'
        ],
        'dataclip_fields': [
            'CREATOR_ROLE',
            'ADJUNCT_ROLE',
            'LOCATION_CLASS',
            'ID_CLASS',
            'FORM',
            'TYPE',
            'MEDIUM',
            'CLASS',
            'STATUS',
            'RELATED_BIBCLASS',
            'INTERNET_CLASS'
        ]
    },
    Table.BIOGRAPHY.value: {
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
        'id_fields': [
            'BIOID',
            'TITLE_GEOID',
            'MILESTONE_GEOID',
            'AFFILIATION_GEOID',
            'RELATED_BIOID_SUBJECT',
            'RELATED_BIOID_OBJECT',
            'RELATED_INSID',
            'RELATED_BIBID',
            'RELATED_MANID',
            'SUBJECT_GEOID',
            'SUBJECT_INSID',
            'SUBJECT_SUBID'
        ],
        'dataclip_fields': [
            'NAME_CLASS',
            'NAME_NUMBER',
            'NAME_HONORIFIC',
            'TITLE',
            'TITLE_NUMBER',
            'TITLE_CONNECTOR',
            'MILESTONE_CLASS',
            'AFFILIATION_CLASS',
            'AFFILIATION_TYPE',
            # Note: the next line is columns that were created by splits
            'AFFILIATION_TYPE_PRO', 'AFFILIATION_TYPE_ORD', 'AFFILIATION_TYPE_REL',
            'SEX',
            'RELATED_BIOCLASS',
            'RELATED_INSCLASS',
            'RELATED_BIBCLASS',
            'RELATED_MANCLASS',
            'INTERNET_CLASS'
        ]
    },
    Table.COPIES.value: {
        'id_fields': [
            'COPID',
            'TEXT_MANID',
            'OWNER_ID',
            'OWNER_GEOID',
            'RELATED_BIOID',
            'RELATED_LIBID',
            'RELATED_LIBEVENTGEOID',
            'RELATED_BIBID',
            'RELATED_MANID',
            'RELATED_COPID',
            'SUBJECT_BIOID',
            'SUBJECT_GEOID',
            'SUBJECT_INSID',
            'SUBJECT_SUBID'
        ],
        'dataclip_fields': [
            'STATUS',
            'MATERIAL',
            'FORMAT',
            'LEAF_CLASS',
            'SIZE_CLASS',
            'PAGE_CLASS',
            'FONT_CLASS',
            'WATERMARK_CLASS',
            'GRAPHIC_CLASS',
            'MUSIC_CLASS',
            'FEATURE_CLASS',
            'RELATED_BIOCLASS',
            'RELATED_LIBCALLNOCLASS',
            'RELATED_LIBEVENTCLASS',
            'RELATED_BIBCLASS',
            'RELATED_MANCLASS',
            'RELATED_COPCLASS',
            'INTERNET_CLASS'
        ]
    },
    Table.GEOGRAPHY.value: {
        'id_fields': [
            'GEOID', 'RELATED_GEOID_S', 'RELATED_GEOID_P', 'RELATED_BIBID', 'RELATED_MANID',
            'SUBJECT_BIOID', 'SUBJECT_INSID', 'SUBJECT_SUBID'
        ],
        'dataclip_fields': [
            'NAME_CLASS', 'CLASS', 'TYPE', 'RELATED_GEOCLASS', 'RELATED_BIBCLASS', 'RELATED_MANCLASS', 'INTERNET_CLASS'
        ]
    },
    Table.INSTITUTIONS.value: {
        'id_fields': [
            "INSID",
            "MILESTONE_GEOID",
            "RELATED_GEOID",
            "RELATED_INSID",
            "RELATED_BIBID",
            "RELATED_MANID",
            "SUBJECT_BIOID",
            "SUBJECT_GEOID",
            "SUBJECT_SUBID"
        ],
        'dataclip_fields': [
            "NAME_CLASS",
            "MILESTONE_CLASS",
            "CLASS", "TYPE",
            "RELATED_GEOCLASS",
            "RELATED_INSCLASS",
            "RELATED_BIBCLASS",
            "RELATED_MANCLASS",
            "INTERNET_CLASS"
        ]
    },
    Table.LIBRARY.value: {
        'id_fields': [
            'LIBID',
            'RELATED_GEOID',
            'RELATED_INSID',
            'RELATED_BIBID',
            'SUBJECT_BIOID',
            'SUBJECT_GEOID',
            'SUBJECT_INSID',
            'SUBJECT_SUBID'
        ],
        'dataclip_fields': [
            'NAME_CLASS',
            'LIBCODE_CLASS',
            'PHONE_LOC',
            'CLASS',
            'TYPE',
            'RELATED_GEOCLASS',
            'RELATED_INSCLASS',
            'RELATED_BIBCLASS',
            'INTERNET_CLASS'
        ]
    },
    Table.MS_ED.value: {
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
        'id_fields': [
            'MANID',
            'MILESTONE_MAKER_ID_P',
            'MILESTONE_MAKER_ID_W',
            'MILESTONE_FUNDER_ID',
            'MILESTONE_GEOID_P',
            'MILESTONE_GEOID_W',
            'OWNER_ID',
            'OWNER_GEOID',
            'FIRST_ANAID',
            'FIRST_TEXID',
            'RELATED_BIOID',
            'RELATED_LIBID',
            'RELATED_LIBEVENTGEOID',
            'RELATED_BIBID',
            'RELATED_MANID',
            'RELATED_UNIID',
            'RELATED_UNILANGUAGE',
            'SUBJECT_BIOID',
            'SUBJECT_GEOID',
            'SUBJECT_INSID',
            'SUBJECT_SUBID'
        ],
        'dataclip_fields': [
            'STATUS',
            'MATERIAL',
            'FORMAT',
            'LEAF_CLASS',
            'SIZE_CLASS',
            'PAGE_CLASS',
            'HAND_CLASS',
            'FONT_CLASS',
            'WATERMARK_CLASS',
            'GRAPHIC_CLASS',
            'MUSIC_CLASS',
            'FEATURE_CLASS',
            'MILESTONE_CLASS',
            'MILESTONE_CLASS_P',
            'MILESTONE_CLASS_W',
            'CLASS',
            'RELATED_BIOCLASS',
            'RELATED_LIBCALLNOCLASS',
            'RELATED_LIBEVENTCLASS',
            'RELATED_BIBCLASS',
            'RELATED_MANCLASS',
            'RELATED_UNICLASS',
            'INTERNET_CLASS'
        ]
    },
    Table.SUBJECT.value: {
        'id_fields': [
            'SUBID',
            'HB_SUBID',
            'HR_SUBID',
            'RELATED_BIBID',
            'RELATED_MANID'
        ],
        'dataclip_fields': [
            'HM_CLASS',
            'HM_TYPE',
            'HV_CLASS',
            'HV_TYPE',
            'RELATED_BIBCLASS',
            'RELATED_MANCLASS',
            'INTERNET_CLASS'
        ]
    },
    Table.UNIFORM_TITLE.value: {
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
        },
        'id_fields': [
            'TEXID',
            'AUTHOR_ID',
            'MILESTONE_GEOID',
            'RELATED_BIOID',
            'RELATED_BIBID',
            'RELATED_MANID',
            'RELATED_UNIID',
            'SUBJECT_BIOID',
            'SUBJECT_GEOID',
            'SUBJECT_INSID',
            'SUBJECT_SUBID'
        ],
        'dataclip_fields': [
            'INC_EXP_CLASS',
            'LANGUAGE_TEXT',
            'LANGUAGE_ORIG',
            'LANGUAGE_INTR',
            'MILESTONE_CLASS',
            'CLASS',
            'RELATED_BIOCLASS',
            'RELATED_BIBCLASS',
            'RELATED_MANCLASS',
            'RELATED_UNICLASS',
            'INTERNET_CLASS',
            'TYPE'
        ]
    }
}
