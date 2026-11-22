"""Красная книга — животные. Тот же каталог, что и у растений; раздел выбирается в app.py (rb_kingdom='animalia')."""
import pathlib
import runpy

runpy.run_path(str(pathlib.Path(__file__).with_name("redbook.py")), run_name="__main__")
