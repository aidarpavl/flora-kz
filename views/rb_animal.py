"""Страница вида животного из Красной книги (редактирование — как у растений)."""
import pathlib
import runpy

runpy.run_path(str(pathlib.Path(__file__).with_name("rb_species.py")), run_name="__main__")
