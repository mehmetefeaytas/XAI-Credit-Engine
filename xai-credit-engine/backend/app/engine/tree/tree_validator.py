"""
engine/tree/tree_validator.py
──────────────────────────────────────────────────────────────────────────────
Karar Ağacı Yapısı Doğrulayıcısı — Graf Teorisi Tabanlı

7 matematiksel kural kontrol edilir:
    1. Tek kök (in-degree = 0 olan tam 1 düğüm)
    2. Kök hariç her düğüm in-degree = 1
    3. Döngü yok (DFS tabanlı cycle detection)
    4. Tüm düğümler kökten erişilebilir (BFS bağlantılılık)
    5. Her iç düğümde tam 2 çocuk (binary tree)
    6. Yaprak etiketleri geçerli ("APPROVED" / "REJECTED")
    7. Her (source, branch_value) çifti benzersiz (determinizm garantisi)

Eğer herhangi bir kontrol başarısız olursa ValidationResult.is_valid = False
ve errors listesinde açıklama yer alır.
"""

from collections import deque
from dataclasses import dataclass, field

from app.domain.models.decision_node import DecisionTreeEdge, DecisionTreeNode


VALID_LABELS = {"APPROVED", "REJECTED"}


@dataclass
class ValidationResult:
    """
    Doğrulama sonucu.

    Attributes:
        is_valid:  Tüm kontroller geçtiyse True
        errors:    Kritik hatalar (bunlar varsa ağaç kullanılamaz)
        warnings:  Uyarılar (kullanılabilir ama dikkat edilmeli)
    """
    is_valid:  bool
    errors:    list[str] = field(default_factory=list)
    warnings:  list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        status = "GEÇERLİ ✓" if self.is_valid else "GEÇERSİZ ✗"
        return (
            f"ValidationResult({status}, "
            f"errors={len(self.errors)}, "
            f"warnings={len(self.warnings)})"
        )


class TreeValidator:
    """
    Karar ağacının matematiksel anlamda geçerli olduğunu doğrular.

    Kullanım:
        validator = TreeValidator()
        result = validator.validate(nodes, edges)
        if not result.is_valid:
            print(result.errors)
    """

    def validate(
        self,
        nodes: list[DecisionTreeNode],
        edges: list[DecisionTreeEdge]
    ) -> ValidationResult:
        """
        7 kontrolü sırayla çalıştırır.

        Args:
            nodes: Tüm düğüm listesi
            edges: Tüm kenar listesi

        Returns:
            ValidationResult — tüm hatalar ve uyarılar dahil
        """
        errors:   list[str] = []
        warnings: list[str] = []

        if not nodes:
            return ValidationResult(
                is_valid=False,
                errors=["Düğüm listesi boş: geçerli bir ağaç değil."]
            )

        # Yapıları hazırla
        node_map: dict = {n.id: n for n in nodes}
        adj       = self._build_adjacency(edges)
        in_degree = self._build_in_degree(nodes, edges)

        # ── KONTROL 1: KÖK BENZERSİZLİĞİ ─────────────────────────────────
        errors.extend(self._check_root_uniqueness(nodes, in_degree))

        # ── KONTROL 2: IN-DEGREE KURALI ────────────────────────────────────
        errors.extend(self._check_in_degrees(nodes, in_degree))

        # ── KONTROL 3: CYCLE TESPİTİ ───────────────────────────────────────
        roots = [n for n in nodes if in_degree.get(n.id, 0) == 0]
        if len(roots) == 1:
            if self._detect_cycles(roots[0].id, adj):
                errors.append("Döngü tespit edildi: geçerli yönlü asiklik ağaç (DAG) değil.")
        elif len(roots) > 1:
            warnings.append("Birden fazla kök: cycle detection atlandı.")

        # ── KONTROL 4: ERİŞİLEBİLİRLİK ────────────────────────────────────
        if len(roots) == 1:
            errors.extend(self._check_connectivity(nodes, adj, roots[0].id))

        # ── KONTROL 5: İKİLİ AĞAÇ KURALI ──────────────────────────────────
        errors.extend(self._check_binary_tree(nodes, edges, adj))

        # ── KONTROL 6: YAPRAK ETİKETİ ──────────────────────────────────────
        errors.extend(self._check_leaf_labels(nodes))

        # ── KONTROL 7: EDGE DETERMİNİZMİ ──────────────────────────────────
        errors.extend(self._check_edge_determinism(edges))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    # ────────────────────────────────────────────────────────────────────────
    # Yardımcı yapı inşacıları
    # ────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_adjacency(edges: list[DecisionTreeEdge]) -> dict:
        """
        Komşuluk listesi: {source_id: [target_id, ...]}
        """
        adj: dict = {}
        for e in edges:
            adj.setdefault(e.source_node_id, []).append(e.target_node_id)
        return adj

    @staticmethod
    def _build_in_degree(
        nodes: list[DecisionTreeNode],
        edges: list[DecisionTreeEdge]
    ) -> dict:
        """
        Her düğüm için gelen kenar sayısı: {node_id: int}
        """
        in_deg = {n.id: 0 for n in nodes}
        for e in edges:
            if e.target_node_id in in_deg:
                in_deg[e.target_node_id] += 1
        return in_deg

    # ────────────────────────────────────────────────────────────────────────
    # Kontrol fonksiyonları
    # ────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _check_root_uniqueness(
        nodes: list[DecisionTreeNode],
        in_degree: dict
    ) -> list[str]:
        """Kontrol 1: Tam bir kök olmalı."""
        errors = []
        roots = [n for n in nodes if in_degree.get(n.id, 0) == 0]

        if len(roots) == 0:
            errors.append(
                "Kök bulunamadı: tüm düğümlerin in-degree > 0. "
                "Döngülü bir yapı olabilir."
            )
        elif len(roots) > 1:
            root_ids = [str(r.id)[:8] + "..." for r in roots]
            errors.append(
                f"Birden fazla kök bulundu ({len(roots)} adet): {root_ids}. "
                f"Ağaç birleşik olmalı."
            )
        return errors

    @staticmethod
    def _check_in_degrees(
        nodes: list[DecisionTreeNode],
        in_degree: dict
    ) -> list[str]:
        """Kontrol 2: Kök hariç her düğüm in-degree = 1."""
        errors = []
        roots = {n.id for n in nodes if in_degree.get(n.id, 0) == 0}

        for node in nodes:
            if node.id in roots:
                continue
            deg = in_degree.get(node.id, 0)
            if deg != 1:
                errors.append(
                    f"Düğüm {str(node.id)[:8]}... in-degree={deg}, beklenen 1. "
                    f"(feature='{node.feature_name}')"
                )
        return errors

    @staticmethod
    def _detect_cycles(root_id, adj: dict) -> bool:
        """
        Kontrol 3: DFS tabanlı cycle tespiti.

        Geri kenar (back edge) varsa → döngü var.
        """
        visited:   set = set()
        rec_stack: set = set()

        def dfs(node_id) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in adj.get(node_id, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True  # Geri kenar → döngü

            rec_stack.discard(node_id)
            return False

        return dfs(root_id)

    @staticmethod
    def _check_connectivity(
        nodes: list[DecisionTreeNode],
        adj: dict,
        root_id
    ) -> list[str]:
        """Kontrol 4: BFS ile tüm düğümlerin kökten erişilebilir olduğunu doğrula."""
        errors = []
        all_ids = {n.id for n in nodes}

        # BFS
        reachable: set = set()
        queue = deque([root_id])
        while queue:
            current = queue.popleft()
            reachable.add(current)
            for neighbor in adj.get(current, []):
                if neighbor not in reachable:
                    queue.append(neighbor)

        unreachable = all_ids - reachable
        if unreachable:
            ids_str = [str(uid)[:8] + "..." for uid in unreachable]
            errors.append(
                f"{len(unreachable)} erişilemeyen düğüm bulundu: {ids_str}"
            )
        return errors

    @staticmethod
    def _check_binary_tree(
        nodes: list[DecisionTreeNode],
        edges: list[DecisionTreeEdge],
        adj: dict
    ) -> list[str]:
        """Kontrol 5: Her iç düğümün tam 2 çocuğu olmalı (True ve False)."""
        errors = []

        # Her kaynak düğümün branch_value dağılımını hesapla
        branch_map: dict = {}  # {source_id: {True: count, False: count}}
        for e in edges:
            branch_map.setdefault(e.source_node_id, {True: 0, False: 0})
            branch_map[e.source_node_id][e.branch_value] = \
                branch_map[e.source_node_id].get(e.branch_value, 0) + 1

        for node in nodes:
            if node.is_leaf:
                continue

            children = adj.get(node.id, [])
            if len(children) != 2:
                errors.append(
                    f"İç düğüm {str(node.id)[:8]}... ('{node.feature_name}') "
                    f"çocuk sayısı {len(children)}, beklenen 2."
                )

            branches = branch_map.get(node.id, {})
            if not (branches.get(True, 0) == 1 and branches.get(False, 0) == 1):
                errors.append(
                    f"Düğüm {str(node.id)[:8]}... için TRUE ve FALSE dalları eksik. "
                    f"Mevcut: {branches}"
                )

        return errors

    @staticmethod
    def _check_leaf_labels(nodes: list[DecisionTreeNode]) -> list[str]:
        """Kontrol 6: Yaprak etiketleri geçerli değerde olmalı."""
        errors = []
        for node in nodes:
            if node.is_leaf:
                if not node.leaf_label:
                    errors.append(
                        f"Yaprak düğüm {str(node.id)[:8]}... etiket içermiyor."
                    )
                elif node.leaf_label not in VALID_LABELS:
                    errors.append(
                        f"Geçersiz yaprak etiketi: '{node.leaf_label}'. "
                        f"Geçerli değerler: {VALID_LABELS}"
                    )
        return errors

    @staticmethod
    def _check_edge_determinism(edges: list[DecisionTreeEdge]) -> list[str]:
        """Kontrol 7: UNIQUE(source_node_id, branch_value) — ağaç determinizmi."""
        errors = []
        seen: set = set()

        for e in edges:
            key = (e.source_node_id, e.branch_value)
            if key in seen:
                branch_str = "TRUE" if e.branch_value else "FALSE"
                errors.append(
                    f"Aynı (source={str(e.source_node_id)[:8]}..., "
                    f"branch={branch_str}) çifti birden fazla kez tanımlı. "
                    f"Determinizm ihlali."
                )
            seen.add(key)

        return errors
