"""Run every test module. Returns non-zero if any fails."""
import importlib
import sys
import traceback

TEST_MODULES = [
    "tests.test_core",
    "tests.test_is_solved",
    "tests.test_harness",
    "tests.test_judge_server",
    "tests.test_fine_server",
    "tests.test_medium_server",
    "tests.test_coarse_server",
]


def main() -> int:
    failures = 0
    for mod_name in TEST_MODULES:
        print(f"\n=== {mod_name} ===")
        try:
            mod = importlib.import_module(mod_name)
            main_fn = getattr(mod, "main", None)
            if main_fn is None:
                # Modules without a main() use the if __name__ == "__main__" block;
                # rerun via importlib won't trigger that, so call individual tests.
                for name in dir(mod):
                    if name.startswith("test_"):
                        fn = getattr(mod, name)
                        try:
                            fn()
                            print(f"  ok  {name}")
                        except Exception as e:
                            failures += 1
                            print(f"  FAIL {name}: {e}")
                continue
            import inspect
            if inspect.iscoroutinefunction(main_fn):
                import asyncio
                asyncio.run(main_fn())
            else:
                rc = main_fn()
                if isinstance(rc, int) and rc != 0:
                    failures += 1
        except SystemExit as e:
            if e.code:
                failures += 1
        except Exception:
            failures += 1
            traceback.print_exc()
    print(f"\n{'=' * 30}")
    print(f"{'OK' if failures == 0 else 'FAILURES: ' + str(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
