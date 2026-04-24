import math

from app.config import get_settings


def object_key_from_detection(det: dict) -> str:
    """Build a stable key for persistence and Gemini label carry-over."""
    tid = det.get("track_id", -1)
    label = det.get("label", "object")
    if tid > -1:
        return f"{label}_{tid}"

    bbox = det.get("bbox", [0, 0, 0, 0])
    cx = int((bbox[0] + bbox[2]) / 2) if len(bbox) == 4 else 0
    cy = int((bbox[1] + bbox[3]) / 2) if len(bbox) == 4 else 0
    cell_x = cx // get_settings().fallback_key_bucket_px
    cell_y = cy // get_settings().fallback_key_bucket_px
    z_val = float(det.get("position_3d", {}).get("z", 0.0))
    z_bucket = int(round(z_val * 2.0))
    return f"{label}_cell_{cell_x}_{cell_y}_{z_bucket}"


def rotation_matrix_from_orientation(alpha: float, beta: float, gamma: float):
    """
    Convert device orientation angles (degrees) to a 3x3 rotation matrix.
    Approximation: R = Rz(alpha) * Rx(beta) * Ry(gamma).
    """
    a = math.radians(alpha)
    b = math.radians(beta)
    g = math.radians(gamma)

    ca, sa = math.cos(a), math.sin(a)
    cb, sb = math.cos(b), math.sin(b)
    cg, sg = math.cos(g), math.sin(g)

    rz = [
        [ca, -sa, 0.0],
        [sa, ca, 0.0],
        [0.0, 0.0, 1.0],
    ]
    rx = [
        [1.0, 0.0, 0.0],
        [0.0, cb, -sb],
        [0.0, sb, cb],
    ]
    ry = [
        [cg, 0.0, sg],
        [0.0, 1.0, 0.0],
        [-sg, 0.0, cg],
    ]

    def matmul(a3, b3):
        return [
            [
                a3[i][0] * b3[0][j] + a3[i][1] * b3[1][j] + a3[i][2] * b3[2][j]
                for j in range(3)
            ]
            for i in range(3)
        ]

    return matmul(matmul(rz, rx), ry)


def pose_matrix_str_from_orientation(alpha: float, beta: float, gamma: float) -> str:
    rot = rotation_matrix_from_orientation(alpha, beta, gamma)
    pose = [
        [rot[0][0], rot[0][1], rot[0][2], 0.0],
        [rot[1][0], rot[1][1], rot[1][2], 0.0],
        [rot[2][0], rot[2][1], rot[2][2], 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    return ",".join(str(pose[r][c]) for r in range(4) for c in range(4))


def euclidean_distance(a: dict, b: dict) -> float:
    ax, ay, az = float(a.get("x", 0.0)), float(a.get("y", 0.0)), float(a.get("z", 0.0))
    bx, by, bz = float(b.get("x", 0.0)), float(b.get("y", 0.0)), float(b.get("z", 0.0))
    try:
        from scipy.spatial.distance import euclidean

        return float(euclidean([ax, ay, az], [bx, by, bz]))
    except Exception:
        dx, dy, dz = ax - bx, ay - by, az - bz
        return math.sqrt(dx * dx + dy * dy + dz * dz)
