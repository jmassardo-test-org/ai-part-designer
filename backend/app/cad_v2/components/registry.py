"""Component registry for CAD v2.

The registry provides lookup of components by ID or natural language alias.
Components are registered at module load time and can be queried with
exact match, alias match, or fuzzy matching.
"""

from difflib import SequenceMatcher

from app.cad_v2.schemas.components import (
    ComponentCategory,
    ComponentDefinition,
)


class ComponentMatch:
    """Result of a component lookup."""

    def __init__(
        self,
        component: ComponentDefinition,
        score: float,
        match_type: str,
    ) -> None:
        """Initialize match result.

        Args:
            component: The matched component definition.
            score: Match confidence (0.0 to 1.0).
            match_type: How the match was made ('exact', 'alias', 'fuzzy').
        """
        self.component = component
        self.score = score
        self.match_type = match_type

    def __repr__(self) -> str:
        return (
            f"ComponentMatch({self.component.id}, score={self.score:.2f}, type={self.match_type})"
        )


class AmbiguousMatchError(Exception):
    """Raised when a query matches multiple components equally."""

    def __init__(self, query: str, matches: list[ComponentMatch]) -> None:
        self.query = query
        self.matches = matches
        match_ids = [m.component.id for m in matches]
        super().__init__(
            f"Ambiguous query '{query}' matches: {match_ids}. Please be more specific."
        )


class ComponentNotFoundError(Exception):
    """Raised when no component matches the query."""

    def __init__(self, query: str, suggestions: list[str] | None = None) -> None:
        self.query = query
        self.suggestions = suggestions or []
        msg = f"No component found matching '{query}'."
        if self.suggestions:
            msg += f" Did you mean: {', '.join(self.suggestions[:3])}?"
        super().__init__(msg)


class ComponentRegistry:
    """Registry of known components.

    Provides lookup by exact ID, alias, or fuzzy matching.
    Thread-safe for reads after initialization.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._components: dict[str, ComponentDefinition] = {}
        self._alias_index: dict[str, str] = {}  # alias -> component_id
        self._category_index: dict[ComponentCategory, list[str]] = {}

    def register(self, component: ComponentDefinition) -> None:
        """Register a component.

        Args:
            component: The component definition to register.

        Raises:
            ValueError: If component ID is already registered.
        """
        if component.id in self._components:
            raise ValueError(f"Component '{component.id}' already registered")

        self._components[component.id] = component

        # Index aliases
        for alias in component.aliases:
            normalized = alias.lower().strip()
            self._alias_index[normalized] = component.id

        # Also index the name
        self._alias_index[component.name.lower().strip()] = component.id
        self._alias_index[component.id.lower()] = component.id

        # Index by category
        if component.category not in self._category_index:
            self._category_index[component.category] = []
        self._category_index[component.category].append(component.id)

    def get(self, component_id: str) -> ComponentDefinition | None:
        """Get component by exact ID.

        Args:
            component_id: The component ID.

        Returns:
            Component definition or None if not found.
        """
        return self._components.get(component_id)

    def get_by_alias(self, alias: str) -> ComponentDefinition | None:
        """Get component by alias.

        Args:
            alias: An alias string (case-insensitive).

        Returns:
            Component definition or None if not found.
        """
        normalized = alias.lower().strip()
        component_id = self._alias_index.get(normalized)
        if component_id:
            return self._components.get(component_id)
        return None

    def search(
        self,
        query: str,
        threshold: float = 0.6,
        max_results: int = 5,
    ) -> list[ComponentMatch]:
        """Search for components matching a query.

        Performs exact match, alias match, then fuzzy match.

        Args:
            query: Search query string.
            threshold: Minimum fuzzy match score (0.0-1.0).
            max_results: Maximum number of results to return.

        Returns:
            List of ComponentMatch results, sorted by score descending.
        """
        query_lower = query.lower().strip()
        results: list[ComponentMatch] = []

        # Exact ID match
        if query_lower in self._components:
            comp = self._components[query_lower]
            results.append(ComponentMatch(comp, 1.0, "exact"))
            return results

        # Alias match
        if query_lower in self._alias_index:
            comp_id = self._alias_index[query_lower]
            comp = self._components[comp_id]
            results.append(ComponentMatch(comp, 1.0, "alias"))
            return results

        # Fuzzy match against IDs and aliases
        seen_ids: set[str] = set()
        for comp_id, comp in self._components.items():
            # Match against ID
            score = SequenceMatcher(None, query_lower, comp_id.lower()).ratio()
            if score >= threshold and comp_id not in seen_ids:
                results.append(ComponentMatch(comp, score, "fuzzy"))
                seen_ids.add(comp_id)

            # Match against name
            name_score = SequenceMatcher(None, query_lower, comp.name.lower()).ratio()
            if name_score > score and name_score >= threshold and comp_id not in seen_ids:
                results.append(ComponentMatch(comp, name_score, "fuzzy"))
                seen_ids.add(comp_id)

            # Match against aliases
            for alias in comp.aliases:
                alias_score = SequenceMatcher(None, query_lower, alias.lower()).ratio()
                if alias_score >= threshold and comp_id not in seen_ids:
                    results.append(ComponentMatch(comp, alias_score, "fuzzy"))
                    seen_ids.add(comp_id)
                    break

        # Sort by score descending
        results.sort(key=lambda m: m.score, reverse=True)
        return results[:max_results]

    def lookup(self, query: str, threshold: float = 0.6) -> ComponentDefinition:
        """Look up a component, raising errors for ambiguous or not found.

        Args:
            query: Search query string.
            threshold: Minimum fuzzy match score.

        Returns:
            The matched component definition.

        Raises:
            ComponentNotFoundError: If no component matches.
            AmbiguousMatchError: If multiple components match equally.
        """
        results = self.search(query, threshold)

        if not results:
            # Get suggestions
            all_results = self.search(query, threshold=0.3, max_results=3)
            suggestions = [r.component.id for r in all_results]
            raise ComponentNotFoundError(query, suggestions)

        # Check for ambiguous match (multiple with same top score)
        if len(results) > 1 and results[0].score == results[1].score:
            ambiguous = [r for r in results if r.score == results[0].score]
            raise AmbiguousMatchError(query, ambiguous)

        return results[0].component

    def list_category(self, category: ComponentCategory) -> list[ComponentDefinition]:
        """List all components in a category.

        Args:
            category: The category to list.

        Returns:
            List of component definitions.
        """
        component_ids = self._category_index.get(category, [])
        return [self._components[cid] for cid in component_ids]

    def list_all(self) -> list[ComponentDefinition]:
        """List all registered components.

        Returns:
            List of all component definitions.
        """
        return list(self._components.values())

    @property
    def count(self) -> int:
        """Number of registered components."""
        return len(self._components)


# Global registry instance
_registry: ComponentRegistry | None = None


def get_registry() -> ComponentRegistry:
    """Get the global component registry.

    Lazily initializes and populates the registry on first call.

    Returns:
        The global ComponentRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = ComponentRegistry()
        _populate_registry(_registry)
    return _registry


def _populate_registry(registry: ComponentRegistry) -> None:
    """Populate the registry with known components."""
    # Import component definitions
    from app.cad_v2.components.boards import get_board_components
    from app.cad_v2.components.connectors import get_connector_components
    from app.cad_v2.components.displays import get_display_components
    from app.cad_v2.components.inputs import get_input_components

    for component in get_board_components():
        registry.register(component)

    for component in get_display_components():
        registry.register(component)

    for component in get_input_components():
        registry.register(component)

    for component in get_connector_components():
        registry.register(component)
