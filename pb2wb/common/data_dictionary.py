from common.enums import Table

# This is a representation of the data dictionary

# Eventually, it should contain every column for every table, organized by editbox

DATADICT = {
    Table.ANALYTIC.value: {
        'Incipits & Explicits': {
            'primary': 'INC_EXP_CLASS',
            'columns': [
                "INCIPIT",
                "INCIPIT_LOC",
                "EXPLICIT",
                "EXPLICIT_LOC",
            ],
            'default': 'ANALYTIC*INC_EXP_CLASS'
        },
        'INTERNET': {
            'primary': 'INTERNET_CLASS',
            'columns': [
                "INTERNET_ADDRESS",
                "INTERNET_SERVICE",
                "INTERNET_LASTSEEN",
            ],
            'default': 'UNIVERSAL*INTERNET_CLASS*URL'
        },
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
        'Milestones': {
            'primary': 'MILESTONE_CLASS',
            'secondary': 'MILESTONE_DETAIL',
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
        'Titles': {
            'primary': 'TITLE',
            'columns': [
                "TITLE_NUMBER",
                "TITLE_CONNECTOR",
                "TITLE_GEOID",
                "TITLE_Q",
                "TITLE_BD",
                "TITLE_BDQ",
                "TITLE_ED",
                "TITLE_EDQ",
                "TITLE_BASIS"
            ],
            'default': 'BIOGRAPHY*TITLE'
        },
        'Affiliations': {
            'primary': 'AFFILIATION_CLASS',
            'columns': [
                "AFFILIATION_TYPE",
                "AFFILIATION_Q",
                "AFFILIATION_GEOID",
                "AFFILIATION_GEOIDQ",
                "AFFILIATION_BD",
                "AFFILIATION_BDQ",
                "AFFILIATION_ED",
                "AFFILIATION_EDQ",
                "AFFILIATION_BASIS",
            ],
            'default': 'BIOGRAPHY*AFFILIATION_CLASS*PRO'
        },
        'Related_Bio': {
            'primary': 'RELATED_BIOCLASS_WITH_SEX',
            'columns': [
                'RELATED_BIOCLASS',
                'RELATED_BIODETAIL',
                'RELATED_BIOID',
                'RELATED_BIOIDQ',
                'RELATED_BIOBD',
                'RELATED_BIOBDQ',
                'RELATED_BIOED',
                'RELATED_BIOEDQ',
                'RELATED_BIOBASIS'
            ],
            'default': 'BIOGRAPHY*AFFILIATION_CLASS*PRO'
        },
        'id_fields': [
            'BIOID',
            'TITLE_GEOID',
            'MILESTONE_GEOID',
            'AFFILIATION_GEOID',
            'RELATED_BIOID',
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
        'Related Copies': {
            'primary': 'RELATED_COPCLASS',
            'columns': [
                "RELATED_COPDETAIL",
                "RELATED_COPID",
                "RELATED_COPBASIS",
            ],
            'default': 'COPIES*RELATED_COPCLASS'
        },
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
        'Names': {
            'primary': 'NAME_CLASS',
            'columns': [
                "NAME",
                "NAME_Q",
                "NAME_BD",
                "NAME_BDQ",
                "NAME_ED",
                "NAME_EDQ",
                "NAME_BASIS",
            ],
            'default': 'GEOGRAPHY*NAME'
        },
        'Related Places': {
            'primary': 'RELATED_GEOCLASS',
            'columns': [
                "RELATED_GEODETAIL",
                "RELATED_GEOID",
                "RELATED_GEOIDQ",
                "RELATED_GEOBD",
                "RELATED_GEOBDQ",
                "RELATED_GEOED",
                "RELATED_GEOEDQ",
                "RELATED_GEOBASIS",
            ],
            'default': 'GEOGRAPHY*RELATED_GEOCLASS'
        },
        'id_fields': [
            'GEOID', 'RELATED_GEOID', 'RELATED_GEOID_S', 'RELATED_GEOID_P', 'RELATED_BIBID', 'RELATED_MANID',
            'SUBJECT_BIOID', 'SUBJECT_INSID', 'SUBJECT_SUBID'
        ],
        'dataclip_fields': [
            'NAME_CLASS', 'CLASS', 'TYPE', 'RELATED_GEOCLASS', 'RELATED_BIBCLASS', 'RELATED_MANCLASS', 'INTERNET_CLASS'
        ]
    },
    Table.INSTITUTIONS.value: {
        'Names': {
            'primary': 'NAME_CLASS',
            'columns': [
                "NAME",
                "NAME_Q",
                "NAME_BD",
                "NAME_BDQ",
                "NAME_ED",
                "NAME_EDQ",
                "NAME_BASIS",
            ],
            'default': 'INSTITUTIONS*NAME_CLASS'
        },
        'Milestones': {
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
                "MILESTONE_BASIS",
            ],
            'default': 'INSTITUTIONS*MILESTONE'
        },
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
        'Names': {
            'primary': 'NAME_CLASS',
            'columns': [
                "NAME",
                "NAME_Q",
                "NAME_BD",
                "NAME_BDQ",
                "NAME_ED",
                "NAME_EDQ",
                "NAME_BASIS",
            ],
            'default': 'LIBRARY*NAME'
        },
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
        'Call Numbers': {
            'primary': 'RELATED_LIBCALLNOCLASS',
            'columns': [
                "RELATED_LIBCALLNO"
            ],
            'default': 'MS_ED*RELATED_LIBCALLNOCLASS'
        },
        'Milestones': {
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
        'History': {
            'primary': 'RELATED_LIBEVENTCLASS',
            'columns': [
                "RELATED_LIBEVENTDETAIL",
                "RELATED_LIBEVENTPRICE",
                "RELATED_LIBEVENTCURRENCY",
                "RELATED_LIBEVENTGEOID",
                "RELATED_LIBEVENTGEOIDQ",
                "RELATED_LIBEVENTBD",
                "RELATED_LIBEVENTBDQ",
                "RELATED_LIBEVENTED",
                "RELATED_LIBEVENTEDQ",
            ],
            'default': 'MS_ED*HISTORY'
        },
        'Size': {
            'primary': 'SIZE_CLASS',
            'columns': [
                "SIZE_HEIGHT",
                "SIZE_WIDTH",
                "SIZE_LOC",
                "SIZE_BASIS",
            ],
            'default': 'MS_ED*SIZE'
        },
        'Page Layout': {
            'primary': 'PAGE_CLASS',
            'columns': [
                "PAGE_DETAIL",
                "PAGE_LOC",
                "PAGE_Q",
                "PAGE_BASIS",
            ],
            'default': 'MS_ED*PAGE'
        },
        'Hands': {
            'primary': 'HAND_CLASS',
            'columns': [
                "HAND_DETAIL",
                "HAND_LOC",
                "HAND_Q",
                "HAND_BASIS",
            ],
            'default': 'MS_ED*HAND'
        },
        'Fonts': {
            'primary': 'FONT_CLASS',
            'columns': [
                "FONT_DETAIL",
                "FONT_LOC",
                "FONT_Q",
                "FONT_BASIS",
            ],
            'default': 'MS_ED*TIPOGRAFIA'
        },
        'Watermarks': {
            'primary': 'WATERMARK_CLASS',
            'columns': [
                "WATERMARK_DETAIL",
                "WATERMARK_LOC",
                "WATERMARK_Q",
                "WATERMARK_BASIS",
            ],
            'default': 'MS_ED*FILIGRANA'
        },
        'Graphics': {
            'primary': 'GRAPHIC_CLASS',
            'columns': [
                "GRAPHIC_DETAIL",
                "GRAPHIC_LOC",
                "GRAPHIC_Q",
                "GRAPHIC_BASIS",
            ],
            'default': 'MAN*GRAPHIC_CLASS'
        },
        'Music': {
            'primary': 'MUSIC_CLASS',
            'columns': [
                "MUSIC_DETAIL",
                "MUSIC_LOC",
                "MUSIC_Q",
                "MUSIC_BASIS",
            ],
            'default': 'MS_ED*MUSIC'
        },
        'Other features': {
            'primary': 'FEATURE_CLASS',
            'columns': [
                "FEATURE_DETAIL",
                "FEATURE_LOC",
                "FEATURE_Q",
                "FEATURE_BASIS",
            ],
            'default': 'MAN*FEATURE_CLASS'
        },
        'Related Uniform Titles': {
            'primary': 'RELATED_UNICLASS',
            'columns': [
                "RELATED_UNIDETAIL",
                "RELATED_UNIID",
                "RELATED_UNILANGUAGE",
                "RELATED_UNIBASIS",
            ],
            'default': 'UNIFORM_TITLE*TIT'
        },
        'Related Copies': {
            'primary': 'RELATED_COPCLASS',
            'columns': [
                "RELATED_COPDETAIL",
                "RELATED_COPID",
                "RELATED_COPBASIS",
            ],
            'default': 'MS_ED*RELATED_COPCLASS'
        },
        'Related Individuals': {
            'primary': 'RELATED_BIOCLASS',
            'columns': [
                "RELATED_BIODETAIL",
                "RELATED_BIOID",
                "RELATED_BIOIDQ",
                "RELATED_BIOBD",
                "RELATED_BIOBDQ",
                "RELATED_BIOED",
                "RELATED_BIOEDQ",
                "RELATED_BIOBASIS",
            ],
            'default': 'MS_ED*RELATED_BIOCLASS*NM'
        },
        'Related manuscripts': {
            'primary': 'RELATED_MANCLASS',
            'columns': [
                "RELATED_MANCLASS",
                "RELATED_MANID",
                "RELATED_MANVOL",
                "RELATED_MANLOC",
                "RELATED_MANITEM",
            ],
            'default': 'MS_ED*RELATED_MANCLASS'
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
        'Variant Headings': {
            'primary': 'HEADING_VARIANT',
            'columns': [
                "HV_CLASS",
                "HV_FIELD",
                "HV_BASIS",
            ],
            'default': 'SUB*HEADING_MAIN'
        },
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
        'Incipits & Explicits': {
            'primary': 'INC_EXP_CLASS',
            'columns': [
                "INCIPIT",
                "EXPLICIT",
            ],
            'default': 'UNIFORM_TITLE*INC_EXP_CLASS'
        },
        'Milestones': {
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
        'Related_Bio': {
            'primary': 'RELATED_BIOCLASS',
            'columns': [
                'RELATED_BIODETAIL',
                'RELATED_BIOID',
                'RELATED_BIOIDQ',
                'RELATED_BIOBD',
                'RELATED_BIOBDQ',
                'RELATED_BIOED',
                'RELATED_BIOEDQ',
                'RELATED_BIOBASIS'
            ],
            'default': 'NONE'
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
