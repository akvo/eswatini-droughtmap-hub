class PublicationStatus:
    in_review = 1
    in_validation = 2
    published = 3

    FieldStr = {
        in_review: "In Review",
        in_validation: "In Validation",
        published: "Published",
    }


class DroughtCategory:
    none = 0
    d0 = 1
    d1 = 2
    d2 = 3
    d3 = 4
    d4 = 5

    FieldStr = {
        none: "Normal or wet conditions",
        d0: "Abnormally Dry",
        d1: "Moderate Drought",
        d2: "Severe Drought",
        d3: "Extreme Drought",
        d4: "Exceptional Drought",
    }
