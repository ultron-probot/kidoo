import glob
import os

def __list_all_modules():
    work_dir = os.path.dirname(__file__)
    mod_paths = glob.glob(work_dir + "/**/*.py", recursive=True)

    all_modules = []
    for f in mod_paths:
        if os.path.isfile(f) and f.endswith(".py") and not f.endswith("__init__.py"):
            relative_path = os.path.relpath(f, work_dir)
            module_name = relative_path.replace(os.sep, ".")[:-3]
            all_modules.append(module_name)

    return all_modules

ALL_MODULES = sorted(__list_all_modules())
__all__ = ALL_MODULES + ["ALL_MODULES"]
