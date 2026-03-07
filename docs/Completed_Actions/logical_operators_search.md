Add logical operators to the search functionality.

The operators should be over a scope, for example:
verse: law AND faith -> find verses that contain both "law" and "faith"
book: law OR faith -> find books that contain either "law" or "faith"
chapter: law XOR faith -> find chapters that contain either "law" or "faith" but not both
verse: law AND NOT faith -> find verses that contain "law" but not "faith"

these should be able to be combined, for example:
verse: law AND (faith OR righteousness) AND NOT (grace OR mercy)

another example of nested scopes:
chapter: (verse: law AND faith) OR (righteousness AND grace)

all of the examples above show what the search bar should be able to do. Here is the highlight behaviour:
verse: highlight verse number
chapter: highlight chapter heading
book: highlight book heading

This search functionality should not interfere with split reading screens and how they currently work