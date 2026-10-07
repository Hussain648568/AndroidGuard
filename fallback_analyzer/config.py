SKIP_PACKAGES = [
    "androidx/", 
    "android/support/", 
    "com/google/", 
    "com/facebook/",
    "kotlin/", 
    "kotlinx/", 
    "okhttp3/", 
    "retrofit2/", 
    "io/reactivex/",
    "rx/", 
    "com/squareup/", 
    "com/bumptech/glide/", 
    "org/apache/"
]

# Scorer Configuration
SCORER_RULES = {
    "HIGH": {
        "link_levels": ["L1", "L2"],
        "require_permission": True,
        "require_exact_match": True
    },
    "MEDIUM": {
        "link_levels": ["L3", "L4"],
        "require_permission": True,
        "allow_name_descriptor_match": True
    }
}
