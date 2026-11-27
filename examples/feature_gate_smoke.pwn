// Compile-only fixture: opt-in code paths must remain syntactically valid.
// This does not enable the experimental detector in the production smoke sample.
#define AC_ENABLE_COMBAT_CADENCE (1)
#include <ac>

main()
{
}

public OnGameModeInit()
{
    AC_Init();
    return 1;
}
