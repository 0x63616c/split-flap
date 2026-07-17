"""Scene — what a model looks like in the viewer.

One abstraction replaces the hand-maintained parallel
objects/names/colors/alphas lists (which silently desync): builders
`add()` each display object with its styling in one call, `show_args()`
produces the kwargs for ocp_vscode.show().
"""

from dataclasses import dataclass, field


@dataclass
class Scene:
    _objects: list = field(default_factory=list)
    _names: list = field(default_factory=list)
    _colors: list = field(default_factory=list)
    _alphas: list = field(default_factory=list)

    def add(self, obj, name: str, color: str | None = None, alpha: float = 1.0, loc=None):
        """Add one display object; loc (a Location/Pos/Rot) poses it."""
        self._objects.append(loc * obj if loc is not None else obj)
        self._names.append(name)
        self._colors.append(color)
        self._alphas.append(alpha)
        return self

    def show_args(self) -> dict:
        """kwargs for ocp_vscode.show(). colors included only when used;
        a scene that colors anything must color everything (no silent
        positional mismatches)."""
        kwargs = dict(objects=self._objects, names=self._names)
        if any(c is not None for c in self._colors):
            missing = [n for n, c in zip(self._names, self._colors) if c is None]
            assert not missing, f"scene colors some objects but not: {missing}"
            kwargs["colors"] = self._colors
        if any(a != 1.0 for a in self._alphas):
            kwargs["alphas"] = self._alphas
        return kwargs
