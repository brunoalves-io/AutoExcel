from __future__ import annotations

import math
import os
import re
import tempfile
from dataclasses import dataclass
from statistics import median
from typing import Any, Iterable


@dataclass
class Token:
    text: str
    x: float
    y: float
    layer: str = ""
    layout: str = ""
    handle: str = ""
    align_x: float | None = None
    align_y: float | None = None


_QUADRA_RE = re.compile(r"\b(?:QUADRA|QDRA|QD)\s*[-_:. ]*0*(\d{1,3})\b", re.IGNORECASE)
_QUADRA_WORD_RE = re.compile(r"\b(?:QUADRA|QDRA)\b", re.IGNORECASE)


def _fix(s: str) -> str:
    return str(s).upper().replace("O", "0").replace("I", "1").replace("L", "1")


def _normalize_quadra_number(raw: str | int) -> str:
    digits = re.sub(r"\D", "", str(raw))
    if not digits:
        return str(raw).strip()
    return str(int(digits)).zfill(max(2, len(digits)))


def _quadra_id(text: str) -> str | None:
    s = str(text or "").replace("\\P", " ").replace("\n", " ")
    m = _QUADRA_RE.search(s)
    if not m:
        return None
    return _normalize_quadra_number(m.group(1))


def _lot(text: str) -> int | None:
    s0 = str(text or "").strip()
    if _quadra_id(s0) is not None or _QUADRA_WORD_RE.search(s0):
        return None
    s = _fix(s0).strip()
    if "," in s or "." in s or "M2" in s or "M²" in s:
        return None
    d = re.sub(r"\D", "", s)
    if not (1 <= len(d) <= 3):
        return None
    n = int(d)
    return n if 1 <= n <= 999 else None


def _area(text: str, int_digits: int, amin: float, amax: float) -> float | None:
    s0 = str(text or "")
    if _quadra_id(s0) is not None or _QUADRA_WORD_RE.search(s0):
        return None
    s = _fix(s0).replace(" ", "")
    m = re.search(r"(\d{2,5})[\.,](\d{2})", s)
    if m:
        v = float(f"{m.group(1)}.{m.group(2)}")
        if amin <= v <= amax:
            return round(v, 2)
    d = re.sub(r"\D", "", s)
    if len(d) == int_digits + 2:
        v = int(d) / 100.0
        if amin <= v <= amax:
            return round(v, 2)
    return None


def _point(entity) -> tuple[float, float] | None:
    for name in ("insert", "align_point", "location"):
        try:
            p = getattr(entity.dxf, name)
            return float(p.x), float(p.y)
        except Exception:
            pass
    return None


def _alignment_point(entity) -> tuple[float, float] | None:
    try:
        typ = entity.dxftype()
    except Exception:
        typ = ""
    if typ not in ("TEXT", "ATTRIB", "ATTDEF"):
        return None
    try:
        placement = entity.get_placement()
        if placement and len(placement) >= 2 and placement[1] is not None:
            p = placement[1]
            return float(p.x), float(p.y)
    except Exception:
        pass
    try:
        p = entity.dxf.align_point
        return float(p.x), float(p.y)
    except Exception:
        return None


def _token_points(t: Token) -> list[tuple[float, float]]:
    pts = [(float(t.x), float(t.y))]
    if t.align_x is not None and t.align_y is not None:
        ap = (float(t.align_x), float(t.align_y))
        if math.hypot(ap[0] - t.x, ap[1] - t.y) > 1e-9:
            pts.append(ap)
    return pts


def _token_point_inside(t: Token, poly: list[tuple[float, float]], tol: float) -> tuple[float, float] | None:
    for p in _token_points(t):
        if _point_in_polygon(p, poly, tol=tol):
            return p
    return None


def _text(entity) -> str | None:
    try:
        typ = entity.dxftype()
        if typ in ("TEXT", "ATTRIB", "ATTDEF"):
            return str(entity.dxf.text)
        if typ == "MTEXT":
            try:
                return str(entity.plain_text())
            except Exception:
                return str(entity.text)
    except Exception:
        return None
    return None


def _walk(layout) -> Iterable[Any]:
    for e in layout:
        yield e
        try:
            if e.dxftype() == "INSERT":
                for a in getattr(e, "attribs", []):
                    yield a
                try:
                    for ve in e.virtual_entities():
                        yield ve
                except Exception:
                    pass
        except Exception:
            pass


def _token_nn_scale(tokens: list[Token]) -> float:
    if len(tokens) < 2:
        return 1.0
    nearest = []
    sample = tokens[:1500]
    for i, a in enumerate(sample):
        best = math.inf
        for j, b in enumerate(sample):
            if i == j:
                continue
            d = math.hypot(a.x - b.x, a.y - b.y)
            if 0 < d < best:
                best = d
        if math.isfinite(best):
            nearest.append(best)
    return median(nearest) if nearest else 1.0


def _detect_quadra_markers(tokens: list[Token]) -> tuple[list[dict[str, Any]], set[int]]:
    markers: list[dict[str, Any]] = []
    reserved: set[int] = set()
    for i, t in enumerate(tokens):
        q = _quadra_id(t.text)
        if q:
            markers.append({"quadra": q, "x": t.x, "y": t.y, "source": t.text, "token_index": i})
            reserved.add(i)
    qwords = [(i, t) for i, t in enumerate(tokens) if i not in reserved and _QUADRA_WORD_RE.search(str(t.text or ""))]
    pure_nums = []
    for i, t in enumerate(tokens):
        if i in reserved:
            continue
        s = str(t.text or "").strip()
        if re.fullmatch(r"0*\d{1,3}", s):
            pure_nums.append((i, t, _normalize_quadra_number(s)))
    scale = _token_nn_scale(tokens)
    max_pair_dist = max(scale * 5.0, 1e-6)
    used_num_tokens: set[int] = set()
    for qi, qt in qwords:
        choices = []
        for ni, nt, qid in pure_nums:
            if ni in used_num_tokens:
                continue
            d = math.hypot(qt.x - nt.x, qt.y - nt.y)
            choices.append((d, ni, nt, qid))
        if not choices:
            continue
        d, ni, nt, qid = min(choices, key=lambda z: z[0])
        if d <= max_pair_dist:
            markers.append({
                "quadra": qid,
                "x": (qt.x + nt.x) / 2.0,
                "y": (qt.y + nt.y) / 2.0,
                "source": f"{qt.text} {nt.text}",
                "token_index": qi,
            })
            reserved.add(qi)
            reserved.add(ni)
            used_num_tokens.add(ni)
    deduped: list[dict[str, Any]] = []
    tol = max(scale * 0.75, 1e-9)
    for m in sorted(markers, key=lambda z: (z["quadra"], z["x"], z["y"])):
        if any(
            d["quadra"] == m["quadra"] and math.hypot(d["x"] - m["x"], d["y"] - m["y"]) <= tol
            for d in deduped
        ):
            continue
        deduped.append(m)
    return deduped, reserved


def _distance_point_segment(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    den = dx * dx + dy * dy
    if den <= 1e-20:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / den
    t = max(0.0, min(1.0, t))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy)


def _point_in_polygon(p: tuple[float, float], poly: list[tuple[float, float]], tol: float = 1e-6) -> bool:
    if len(poly) < 3:
        return False
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        if _distance_point_segment(p, a, b) <= tol:
            return True
    x, y = p
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            cross_x = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < cross_x:
                inside = not inside
        j = i
    return inside


def _polygon_area(poly: list[tuple[float, float]]) -> float:
    if len(poly) < 3:
        return 0.0
    return abs(sum(
        poly[i][0] * poly[(i + 1) % len(poly)][1]
        - poly[(i + 1) % len(poly)][0] * poly[i][1]
        for i in range(len(poly))
    )) / 2.0


def _polygon_center(poly: list[tuple[float, float]]) -> tuple[float, float]:
    a2 = 0.0
    cx = 0.0
    cy = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        a2 += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(a2) > 1e-12:
        return cx / (3.0 * a2), cy / (3.0 * a2)
    return (
        sum(x for x, _ in poly) / max(1, n),
        sum(y for _, y in poly) / max(1, n),
    )


def _token_key(t: Token) -> tuple[str, str, float, float]:
    return (str(t.handle or ""), str(t.text or ""), round(float(t.x), 8), round(float(t.y), 8))


def _token_distance_to_polygon(t: Token, poly: list[tuple[float, float]]) -> tuple[float, tuple[float, float]]:
    best_d = math.inf
    best_p = (float(t.x), float(t.y))
    for pt in _token_points(t):
        if _point_in_polygon(pt, poly, tol=1e-9):
            return 0.0, pt
        d = min(
            _distance_point_segment(pt, poly[i], poly[(i + 1) % len(poly)])
            for i in range(len(poly))
        )
        if d < best_d:
            best_d = d
            best_p = pt
    return best_d, best_p


def _extract_lot_polygons(doc, lots: list[tuple[int, Token]], areas: list[tuple[float, Token]]) -> list[dict[str, Any]]:
    raw_polys: list[dict[str, Any]] = []
    for layout in doc.layouts:
        try:
            entities = layout.query("LWPOLYLINE")
        except Exception:
            continue
        for e in entities:
            try:
                is_closed = bool(e.closed)
                pts = [(float(x), float(y)) for x, y, *_ in e.get_points("xy")]
            except Exception:
                continue
            if len(pts) < 3:
                continue
            edge_lengths = [
                math.hypot(
                    pts[(i + 1) % len(pts)][0] - pts[i][0],
                    pts[(i + 1) % len(pts)][1] - pts[i][1],
                )
                for i in range(len(pts))
            ]
            med_edge = median([d for d in edge_lengths if d > 1e-9]) if edge_lengths else 1.0
            local_tol = max(med_edge * 1e-5, 1e-7)
            contained_lots = []
            for n, t in lots:
                ip = _token_point_inside(t, pts, local_tol)
                if ip is not None:
                    contained_lots.append((n, t, ip))
            contained_areas = []
            for a, t in areas:
                ip = _token_point_inside(t, pts, local_tol)
                if ip is not None:
                    contained_areas.append((a, t, ip))
            polygon_area = _polygon_area(pts)
            implicit_closed = False
            closure_area_error = None
            if not is_closed:
                if len(contained_lots) != 1 or len(contained_areas) != 1:
                    continue
                written_area = float(contained_areas[0][0])
                closure_area_error = abs(float(polygon_area) - written_area)
                allowed_error = max(0.50, written_area * 0.005)
                if closure_area_error > allowed_error:
                    continue
                implicit_closed = True
            raw_polys.append({
                "handle": str(getattr(e.dxf, "handle", "") or ""),
                "layout": getattr(layout, "name", "") or "",
                "points": pts,
                "center": _polygon_center(pts),
                "polygon_area": polygon_area,
                "med_edge": med_edge,
                "local_tol": local_tol,
                "contained_lots": contained_lots,
                "contained_areas": contained_areas,
                "implicit_closed": implicit_closed,
                "closure_area_error": closure_area_error,
            })

    result: list[dict[str, Any]] = []
    used_lots: set[tuple[str, str, float, float]] = set()
    used_areas: set[tuple[str, str, float, float]] = set()

    def append_record(rec, lot_item, area_item, recovered: str | None = None, recovery_distance: float = 0.0):
        n, lt, lot_point = lot_item
        a, at, area_point = area_item
        center = rec["center"]
        result.append({
            "handle": rec["handle"],
            "layout": rec["layout"],
            "points": rec["points"],
            "center_x": center[0],
            "center_y": center[1],
            "polygon_area": rec["polygon_area"],
            "lote": int(n),
            "area_m2": float(a),
            "lot_token": lt,
            "area_token": at,
            "lot_point": lot_point,
            "area_point": area_point,
            "recovered_label": recovered,
            "recovery_distance": float(recovery_distance),
            "implicit_closed": bool(rec.get("implicit_closed")),
            "closure_area_error": rec.get("closure_area_error"),
        })
        used_lots.add(_token_key(lt))
        used_areas.add(_token_key(at))

    unresolved: list[dict[str, Any]] = []
    for rec in raw_polys:
        cl = rec["contained_lots"]
        ca = rec["contained_areas"]
        if len(cl) == 1 and len(ca) == 1:
            append_record(rec, cl[0], ca[0])
        else:
            unresolved.append(rec)

    for rec in unresolved:
        cl = rec["contained_lots"]
        ca = rec["contained_areas"]
        pts = rec["points"]
        med_edge = max(float(rec["med_edge"]), 1e-9)
        relaxed_tol = max(med_edge * 0.03, float(rec["local_tol"]))
        max_pair_dist = max(med_edge * 0.75, relaxed_tol * 4.0)
        if len(cl) == 0 and len(ca) == 1:
            a, at, area_point = ca[0]
            if _token_key(at) in used_areas:
                continue
            candidates = []
            for n, t in lots:
                if _token_key(t) in used_lots:
                    continue
                edge_d, pt = _token_distance_to_polygon(t, pts)
                if edge_d > relaxed_tol:
                    continue
                pair_d = math.hypot(pt[0] - area_point[0], pt[1] - area_point[1])
                if pair_d > max_pair_dist:
                    continue
                score = edge_d + pair_d * 0.08
                candidates.append((score, edge_d, pair_d, n, t, pt))
            candidates.sort(key=lambda z: (z[0], z[1], z[2]))
            if candidates:
                first = candidates[0]
                clear = len(candidates) == 1 or candidates[1][0] >= first[0] + max(med_edge * 0.015, 0.25)
                if clear:
                    _, edge_d, _, n, lt, lot_point = first
                    append_record(rec, (n, lt, lot_point), ca[0], recovered="lote", recovery_distance=edge_d)
        elif len(cl) == 1 and len(ca) == 0:
            n, lt, lot_point = cl[0]
            if _token_key(lt) in used_lots:
                continue
            candidates = []
            for a, t in areas:
                if _token_key(t) in used_areas:
                    continue
                edge_d, pt = _token_distance_to_polygon(t, pts)
                if edge_d > relaxed_tol:
                    continue
                pair_d = math.hypot(pt[0] - lot_point[0], pt[1] - lot_point[1])
                if pair_d > max_pair_dist:
                    continue
                score = edge_d + pair_d * 0.08
                candidates.append((score, edge_d, pair_d, a, t, pt))
            candidates.sort(key=lambda z: (z[0], z[1], z[2]))
            if candidates:
                first = candidates[0]
                clear = len(candidates) == 1 or candidates[1][0] >= first[0] + max(med_edge * 0.015, 0.25)
                if clear:
                    _, edge_d, _, a, at, area_point = first
                    append_record(rec, cl[0], (a, at, area_point), recovered="area", recovery_distance=edge_d)

    progress = True
    while progress:
        progress = False
        for rec in unresolved:
            cl = rec["contained_lots"]
            ca = rec["contained_areas"]
            if len(cl) != 0 or len(ca) != 1:
                continue
            a, at, area_point = ca[0]
            if _token_key(at) in used_areas:
                continue
            pts = rec["points"]
            med_edge = max(float(rec.get("med_edge") or 0.0), 1e-9)
            neighbor_lots: set[int] = set()
            for existing in result:
                other_pts = existing.get("points") or []
                if not other_pts:
                    continue
                other_edges = [
                    math.hypot(
                        other_pts[(i + 1) % len(other_pts)][0] - other_pts[i][0],
                        other_pts[(i + 1) % len(other_pts)][1] - other_pts[i][1],
                    )
                    for i in range(len(other_pts))
                ]
                other_med = median([d for d in other_edges if d > 1e-9]) if other_edges else med_edge
                topo_tol = max(min(med_edge, other_med) * 0.0015, 1e-6)
                if _shared_vertices(pts, other_pts, topo_tol) >= 2 or _shared_vertices(other_pts, pts, topo_tol) >= 2:
                    neighbor_lots.add(int(existing["lote"]))
            inferred_candidates: set[int] = set()
            ordered_neighbors = sorted(neighbor_lots)
            for left in ordered_neighbors:
                if left + 2 in neighbor_lots:
                    inferred_candidates.add(left + 1)
            if len(inferred_candidates) != 1:
                continue
            inferred = next(iter(inferred_candidates))
            center = rec["center"]
            synthetic = Token(
                text=f"{inferred:02d}",
                x=float(center[0]),
                y=float(center[1]),
                layer=str(at.layer or ""),
                layout=str(at.layout or ""),
                handle=f"INFERRED:{rec.get('handle') or inferred}",
            )
            append_record(
                rec,
                (inferred, synthetic, center),
                ca[0],
                recovered="numero_lote_inferido",
                recovery_distance=0.0,
            )
            result[-1]["inferred_lot"] = True
            result[-1]["inferred_from_neighbors"] = sorted(neighbor_lots)
            progress = True

    return result


def _shared_vertices(a: list[tuple[float, float]], b: list[tuple[float, float]], tol: float) -> int:
    count = 0
    for p1 in a:
        if any(math.hypot(p1[0] - p2[0], p1[1] - p2[1]) <= tol for p2 in b):
            count += 1
    return count


def _polygon_components(polygons: list[dict[str, Any]]) -> tuple[list[list[int]], float]:
    if not polygons:
        return [], 0.0
    edges = []
    for p in polygons:
        pts = p["points"]
        edges.extend(
            math.hypot(
                pts[(i + 1) % len(pts)][0] - pts[i][0],
                pts[(i + 1) % len(pts)][1] - pts[i][1],
            )
            for i in range(len(pts))
        )
    typical_edge = median([d for d in edges if d > 1e-9]) if edges else 1.0
    tol = max(typical_edge * 0.001, 1e-6)
    n = len(polygons)
    adj = [set() for _ in range(n)]
    for i in range(n):
        pi = polygons[i]["points"]
        for j in range(i + 1, n):
            pj = polygons[j]["points"]
            if _shared_vertices(pi, pj, tol) >= 2 or _shared_vertices(pj, pi, tol) >= 2:
                adj[i].add(j)
                adj[j].add(i)
    seen: set[int] = set()
    comps: list[list[int]] = []
    for i in range(n):
        if i in seen:
            continue
        stack = [i]
        seen.add(i)
        comp = []
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        comps.append(comp)
    return comps, tol


def _component_center(polygons: list[dict[str, Any]], comp: list[int]) -> tuple[float, float]:
    weights = [max(float(polygons[i].get("polygon_area") or 0.0), 1e-9) for i in comp]
    den = sum(weights)
    return (
        sum(polygons[i]["center_x"] * w for i, w in zip(comp, weights)) / den,
        sum(polygons[i]["center_y"] * w for i, w in zip(comp, weights)) / den,
    )


def _assign_components_to_markers(polygons: list[dict[str, Any]], components: list[list[int]], markers: list[dict[str, Any]]) -> dict[int, str]:
    if not components or not markers:
        return {}
    edges: list[tuple[float, int, int]] = []
    centers: dict[int, tuple[float, float]] = {}
    for ci, comp in enumerate(components):
        cx, cy = _component_center(polygons, comp)
        centers[ci] = (cx, cy)
        for mi, m in enumerate(markers):
            d = math.hypot(cx - m["x"], cy - m["y"])
            edges.append((d, ci, mi))
    assigned: dict[int, str] = {}
    used_markers: set[int] = set()
    for _, ci, mi in sorted(edges, key=lambda z: z[0]):
        if ci in assigned or mi in used_markers:
            continue
        assigned[ci] = str(markers[mi]["quadra"])
        used_markers.add(mi)
    nums_by_comp: dict[int, set[int]] = {
        ci: {int(polygons[i]["lote"]) for i in comp}
        for ci, comp in enumerate(components)
    }
    marker_by_quadra = {str(m["quadra"]): m for m in markers}
    while True:
        progress = False
        nums_by_quadra: dict[str, set[int]] = {}
        comps_by_quadra: dict[str, list[int]] = {}
        for ci, q in assigned.items():
            nums_by_quadra.setdefault(q, set()).update(nums_by_comp[ci])
            comps_by_quadra.setdefault(q, []).append(ci)
        for ci in [idx for idx in range(len(components)) if idx not in assigned]:
            candidate_nums = nums_by_comp[ci]
            candidates: list[tuple[int, float, float, str]] = []
            for q, current_nums in nums_by_quadra.items():
                if candidate_nums & current_nums:
                    continue
                union = current_nums | candidate_nums
                if not union:
                    continue
                lo, hi = min(union), max(union)
                if len(union) != hi - lo + 1:
                    continue
                cx, cy = centers[ci]
                d_component = min(
                    math.hypot(cx - centers[other][0], cy - centers[other][1])
                    for other in comps_by_quadra[q]
                )
                marker = marker_by_quadra.get(q)
                d_marker = math.hypot(cx - marker["x"], cy - marker["y"]) if marker is not None else math.inf
                starts_at_one_penalty = 0 if lo == 1 else 1
                candidates.append((starts_at_one_penalty, d_component, d_marker, q))
            if candidates:
                candidates.sort(key=lambda z: (z[0], z[1], z[2], _quadra_sort_key(z[3])))
                assigned[ci] = candidates[0][3]
                progress = True
        if not progress:
            break
    return assigned


def _rows_from_topology(doc, lots: list[tuple[int, Token]], areas: list[tuple[float, Token]], markers: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    polygons = _extract_lot_polygons(doc, lots, areas)
    if not polygons:
        return [], {"method": "none", "lot_polygons": 0}
    components, adjacency_tol = _polygon_components(polygons)
    comp_to_quadra = _assign_components_to_markers(polygons, components, markers)
    poly_to_comp: dict[int, int] = {}
    for ci, comp in enumerate(components):
        for pi in comp:
            poly_to_comp[pi] = ci
    rows: list[dict[str, Any]] = []
    for pi, p in enumerate(polygons):
        lt: Token = p["lot_token"]
        at: Token = p["area_token"]
        ci = poly_to_comp.get(pi)
        q = comp_to_quadra.get(ci, "SEM_QUADRA") if ci is not None else "SEM_QUADRA"
        lp = p.get("lot_point", (lt.x, lt.y))
        ap = p.get("area_point", (at.x, at.y))
        d = math.hypot(lp[0] - ap[0], lp[1] - ap[1])
        recovered = p.get("recovered_label")
        recovery_distance = float(p.get("recovery_distance") or 0.0)
        implicit_closed = bool(p.get("implicit_closed"))
        closure_area_error = p.get("closure_area_error")
        if recovered == "numero_lote_inferido":
            viz = p.get("inferred_from_neighbors") or []
            viz_txt = " e ".join(f"L.{int(n):02d}" for n in viz) if viz else "lotes vizinhos"
            note = (
                f"número L.{int(p['lote']):02d} inferido com segurança pela continuidade topológica "
                f"entre {viz_txt}; área vinculada pela própria polilinha do DXF"
            )
            confidence = 0.99
        elif implicit_closed and recovered:
            note = (
                f"LWPOLYLINE sem flag CLOSED validada pela área geométrica; "
                f"ponto técnico de {recovered} recuperado a {recovery_distance:.3f} unidade(s) da borda"
            )
            confidence = 0.99
        elif implicit_closed:
            err = float(closure_area_error or 0.0)
            note = (
                "LWPOLYLINE sem flag CLOSED recuperada com segurança: "
                f"fechamento implícito coincide com a área escrita (diferença {err:.3f} m²)"
            )
            confidence = 0.995
        elif recovered:
            note = (
                f"lote e área vinculados pela mesma polilinha; ponto técnico de {recovered} "
                f"recuperado a {recovery_distance:.3f} unidade(s) da borda"
            )
            confidence = 0.99
        else:
            note = "lote e área vinculados pela mesma polilinha fechada do DXF"
            confidence = 1.0
        rows.append({
            "lote": int(p["lote"]),
            "area_m2": float(p["area_m2"]),
            "confidence": confidence,
            "status": "OK" if q != "SEM_QUADRA" else "REVISAR",
            "note": note,
            "lot_raw": lt.text,
            "area_raw": at.text,
            "pair_distance": round(d, 4),
            "x": (lp[0] + ap[0]) / 2.0,
            "y": (lp[1] + ap[1]) / 2.0,
            "lot_layer": lt.layer,
            "area_layer": at.layer,
            "layer_quadra": None,
            "assignment_locked": True,
            "quadra": q,
            "quadra_source": "topologia das polilinhas + rótulo QUADRA",
            "quadra_distance": None,
            "quadra_choices": [],
            "polygon_handle": p["handle"],
            "component_id": (ci + 1) if ci is not None else None,
        })
    component_debug = []
    for ci, comp in enumerate(components):
        nums = sorted(int(polygons[i]["lote"]) for i in comp)
        q = comp_to_quadra.get(ci, "SEM_QUADRA")
        cx, cy = _component_center(polygons, comp)
        expected = list(range(1, max(nums) + 1)) if nums else []
        component_debug.append({
            "component_id": ci + 1,
            "quadra": q,
            "lotes": len(comp),
            "primeiro": min(nums) if nums else None,
            "ultimo": max(nums) if nums else None,
            "sequencia_continua": nums == expected,
            "centro_x": round(cx, 4),
            "centro_y": round(cy, 4),
        })
    recovered = [p for p in polygons if p.get("recovered_label")]
    inferred_lots = [p for p in polygons if p.get("inferred_lot")]
    implicit_closed = [p for p in polygons if p.get("implicit_closed")]
    stats = {
        "method": "topologia de LWPOLYLINE",
        "lot_polygons": len(polygons),
        "implicit_closed_polygons": len(implicit_closed),
        "implicit_closed_details": [
            {
                "polygon_handle": p.get("handle"),
                "lote": p.get("lote"),
                "area_m2": p.get("area_m2"),
                "diferenca_area_m2": round(float(p.get("closure_area_error") or 0.0), 4),
            }
            for p in implicit_closed
        ],
        "recovered_labels": len(recovered),
        "inferred_lots": len(inferred_lots),
        "inferred_lot_details": [
            {
                "polygon_handle": p.get("handle"),
                "lote": p.get("lote"),
                "area_m2": p.get("area_m2"),
                "vizinhos": p.get("inferred_from_neighbors") or [],
            }
            for p in inferred_lots
        ],
        "recovered_details": [
            {
                "polygon_handle": p.get("handle"),
                "lote": p.get("lote"),
                "tipo": p.get("recovered_label"),
                "distancia_borda": round(float(p.get("recovery_distance") or 0.0), 4),
            }
            for p in recovered
        ],
        "components": len(components),
        "adjacency_tolerance": adjacency_tol,
        "component_debug": component_debug,
    }
    return rows, stats


def _pair_lots_areas(lots: list[tuple[int, Token]], areas: list[tuple[float, Token]]) -> list[dict[str, Any]]:
    if not lots or not areas:
        return []
    candidates = []
    for li, (n, lt) in enumerate(lots):
        for ai, (a, at) in enumerate(areas):
            candidates.append((math.hypot(lt.x - at.x, lt.y - at.y), li, ai))
    candidates.sort(key=lambda z: z[0])
    nearest = [min(math.hypot(lt.x - at.x, lt.y - at.y) for _, at in areas) for _, lt in lots]
    med = median(nearest) if nearest else 1.0
    max_d = max(med * 2.5, 1e-9)
    used_l, used_a, rows = set(), set(), []
    for d, li, ai in candidates:
        if li in used_l or ai in used_a or d > max_d:
            continue
        used_l.add(li)
        used_a.add(ai)
        n, lt = lots[li]
        a, at = areas[ai]
        rows.append({
            "lote": int(n),
            "area_m2": float(a),
            "confidence": 0.75,
            "status": "REVISAR",
            "note": "fallback por proximidade; o DXF não ofereceu topologia suficiente",
            "lot_raw": lt.text,
            "area_raw": at.text,
            "pair_distance": round(d, 4),
            "x": (lt.x + at.x) / 2.0,
            "y": (lt.y + at.y) / 2.0,
            "lot_layer": lt.layer,
            "area_layer": at.layer,
            "layer_quadra": None,
            "assignment_locked": False,
        })
    return rows


def _assign_quadras_legacy(rows: list[dict[str, Any]], markers: list[dict[str, Any]]) -> None:
    if not rows:
        return
    if not markers:
        for r in rows:
            r["quadra"] = "SEM_QUADRA"
            r["quadra_source"] = "rótulo QUADRA não encontrado"
            r["status"] = "REVISAR"
        return
    for r in rows:
        choices = sorted(
            (math.hypot(r["x"] - m["x"], r["y"] - m["y"]), str(m["quadra"]))
            for m in markers
        )
        r["quadra_choices"] = [(round(d, 4), q) for d, q in choices[:6]]
        r["quadra"] = choices[0][1]
        r["quadra_distance"] = round(choices[0][0], 4)
        r["quadra_source"] = "fallback: rótulo mais próximo"
        r["status"] = "REVISAR"
        r["note"] += "; confirme a quadra manualmente"


def _quadra_sort_key(q: str):
    parts = re.split(r"(\d+)", str(q))
    return tuple(int(p) if p.isdigit() else p.casefold() for p in parts)


def read_dxf_bytes(
    data: bytes,
    integer_digits: int = 3,
    area_min: float = 100.0,
    area_max: float = 5000.0,
) -> dict[str, Any]:
    import ezdxf

    fd, path = tempfile.mkstemp(suffix=".dxf")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(data)
        doc = ezdxf.readfile(path)
        tokens: list[Token] = []
        for layout in doc.layouts:
            layout_name = getattr(layout, "name", "") or ""
            for e in _walk(layout):
                txt, p = _text(e), _point(e)
                if txt and p:
                    try:
                        layer = str(e.dxf.layer)
                    except Exception:
                        layer = ""
                    try:
                        handle = str(e.dxf.handle)
                    except Exception:
                        handle = ""
                    ap = _alignment_point(e)
                    tokens.append(Token(
                        txt.strip(), p[0], p[1], layer=layer, layout=layout_name, handle=handle,
                        align_x=(ap[0] if ap else None), align_y=(ap[1] if ap else None),
                    ))
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    markers, reserved = _detect_quadra_markers(tokens)
    lots: list[tuple[int, Token]] = []
    areas: list[tuple[float, Token]] = []
    for i, t in enumerate(tokens):
        if i in reserved:
            continue
        n = _lot(t.text)
        a = _area(t.text, integer_digits, area_min, area_max)
        if n is not None:
            lots.append((n, t))
        if a is not None:
            areas.append((a, t))
    if not lots or not areas:
        raise ValueError("Não encontrei números de lote e áreas como TEXT/MTEXT/atributos no DXF.")

    rows, topology_stats = _rows_from_topology(doc, lots, areas, markers)
    expected_pairs = min(len(lots), len(areas))
    topology_coverage = (len(rows) / expected_pairs) if expected_pairs else 0.0
    topology_used = bool(rows) and topology_coverage >= 0.95
    if not topology_used:
        rows = _pair_lots_areas(lots, areas)
        if not rows:
            raise ValueError("Os textos existem no DXF, mas o pareamento lote/área falhou.")
        _assign_quadras_legacy(rows, markers)
        topology_stats = {
            **topology_stats,
            "method": "fallback por proximidade",
            "coverage": round(topology_coverage, 4),
        }
    else:
        topology_stats["coverage"] = round(topology_coverage, 4)

    best: dict[tuple[str, int], dict[str, Any]] = {}
    duplicates_for_review = []
    for r in sorted(rows, key=lambda x: x["pair_distance"]):
        key = (str(r.get("quadra") or "SEM_QUADRA"), int(r["lote"]))
        if key not in best:
            best[key] = r
        else:
            duplicates_for_review.append(r)
    rows = list(best.values()) + duplicates_for_review
    rows.sort(key=lambda x: (_quadra_sort_key(str(x.get("quadra", ""))), int(x["lote"]), x["pair_distance"]))

    counts: dict[tuple[str, int], int] = {}
    for r in rows:
        key = (str(r.get("quadra")), int(r["lote"]))
        counts[key] = counts.get(key, 0) + 1
    for r in rows:
        key = (str(r.get("quadra")), int(r["lote"]))
        if counts[key] > 1:
            r["status"] = "REVISAR"
            r["note"] += "; lote duplicado dentro da mesma quadra"

    by_quadra: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_quadra.setdefault(str(r.get("quadra") or "SEM_QUADRA"), []).append(r)
    by_quadra = dict(sorted(by_quadra.items(), key=lambda kv: _quadra_sort_key(kv[0])))

    detected_qs = [m["quadra"] for m in markers]
    marker_desc = ", ".join(sorted(set(detected_qs), key=_quadra_sort_key)) if detected_qs else "nenhum"
    method_desc = topology_stats.get("method", "leitura direta")
    obs = (
        f"{len(rows)} lote(s) lido(s) diretamente do DXF em {len(by_quadra)} quadra(s). "
        f"Rótulos QUADRA detectados: {marker_desc}. Método: {method_desc}. OCR não foi usado."
    )
    if "SEM_QUADRA" in by_quadra:
        obs += " Há itens SEM_QUADRA; edite a coluna Quadra antes de gerar o Excel."

    return {
        "mode": "DXF multi-quadra",
        "lotes": rows,
        "quadras": by_quadra,
        "observacoes": obs,
        "debug_image": None,
        "stats": {
            "textos": len(tokens),
            "rotulos_quadra": len(markers),
            "quadras_detectadas": sorted(set(detected_qs), key=_quadra_sort_key),
            "candidatos_lote": len(lots),
            "candidatos_area": len(areas),
            "pares": len(rows),
            "quadras_resultado": {q: len(rs) for q, rs in by_quadra.items()},
            "topologia": topology_stats,
            "sequencia_por_quadra": {
                q: {
                    "primeiro": min(int(r["lote"]) for r in rs) if rs else None,
                    "ultimo": max(int(r["lote"]) for r in rs) if rs else None,
                    "ausentes": sorted(
                        set(range(1, max(int(r["lote"]) for r in rs) + 1))
                        - {int(r["lote"]) for r in rs}
                    ) if rs else [],
                }
                for q, rs in by_quadra.items()
            },
        },
        "quadra_markers": markers,
        "raw_tokens": [],
    }
