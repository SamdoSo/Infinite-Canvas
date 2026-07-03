import os
import json
import uuid
import datetime
import shutil
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Tuple

from db.models import User, Project, CanvasMetadata, Asset, SystemConfig

# Helper to resolve user directories
def get_user_dir(user_id: str) -> str:
    """获取用户独立根目录，如 data/users/<user_id>"""
    from main import DATA_DIR
    path = os.path.join(DATA_DIR, "users", user_id)
    os.makedirs(path, exist_ok=True)
    return path

def get_user_canvases_dir(user_id: str) -> str:
    """获取用户的画布 JSON 存储目录"""
    path = os.path.join(get_user_dir(user_id), "canvases")
    os.makedirs(path, exist_ok=True)
    return path

def get_user_assets_dir(user_id: str, subfolder: str = "uploads") -> str:
    """获取用户的素材目录 (uploads 或 output)"""
    path = os.path.join(get_user_dir(user_id), "assets", subfolder)
    os.makedirs(path, exist_ok=True)
    return path

def get_canvas_file_path(user_id: str, canvas_id: str) -> str:
    """获取具体画布 JSON 文件的完整磁盘路径"""
    return os.path.join(get_user_canvases_dir(user_id), f"{canvas_id}.json")

# ==================== PROJECT CRUD ====================

def get_or_create_default_project(db: Session, user_id: str) -> Project:
    """获取或自动创建用户的默认项目"""
    proj = db.query(Project).filter(Project.id == "default", Project.owner_id == user_id).first()
    if not proj:
        # 确保不存在并发冲突，如果已经以 default 创建，则直接使用
        proj = Project(
            id="default",
            name="默认项目",
            owner_id=user_id,
            order=0,
            created_at=datetime.datetime.utcnow()
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)
    return proj

def list_projects_for_user(db: Session, user_id: str) -> List[Dict[str, Any]]:
    """列出用户的全部项目，包含该项目下的画布数量统计"""
    # 确保存在默认项目
    get_or_create_default_project(db, user_id)
    
    # 统计每个项目下的活跃画布数量
    counts = db.query(
        CanvasMetadata.project_id, 
        func.count(CanvasMetadata.id)
    ).filter(
        CanvasMetadata.owner_id == user_id, 
        CanvasMetadata.is_deleted == False
    ).group_by(CanvasMetadata.project_id).all()
    
    counts_dict = {pid: count for pid, count in counts}
    
    projects = db.query(Project).filter(Project.owner_id == user_id).order_by(Project.order.asc(), Project.created_at.asc()).all()
    
    out = []
    for p in projects:
        out.append({
            "id": p.id,
            "name": p.name,
            "order": p.order,
            "created_at": int(p.created_at.timestamp() * 1000),
            "updated_at": int(p.updated_at.timestamp() * 1000),
            "canvas_count": counts_dict.get(p.id, 0)
        })
    return out

def create_project_for_user(db: Session, user_id: str, name: str) -> Project:
    """为用户新建项目"""
    get_or_create_default_project(db, user_id)
    
    # 计算新的 order 序号
    max_order = db.query(func.max(Project.order)).filter(Project.owner_id == user_id).scalar() or 0
    
    proj = Project(
        id=uuid.uuid4().hex,
        name=name[:60],
        owner_id=user_id,
        order=max_order + 1,
        created_at=datetime.datetime.utcnow()
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj

def update_project_for_user(db: Session, user_id: str, project_id: str, name: str = None, order: int = None) -> Project:
    """修改项目信息"""
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).first()
    if not proj:
        return None
    if name is not None:
        proj.name = name[:60]
    if order is not None:
        proj.order = order
    proj.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(proj)
    return proj

def delete_project_for_user(db: Session, user_id: str, project_id: str) -> bool:
    """删除项目，默认项目不能删。其余项目删除后，其下的画布将自动移至“默认项目”下。"""
    if project_id == "default":
        return False
        
    proj = db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).first()
    if not proj:
        return False
        
    # 确保用户的默认项目存在
    get_or_create_default_project(db, user_id)
    
    # 将该项目下的画布迁移回默认项目
    db.query(CanvasMetadata).filter(
        CanvasMetadata.project_id == project_id, 
        CanvasMetadata.owner_id == user_id
    ).update({"project_id": "default"})
    
    # 物理删除磁盘上对应画布 JSON 内的项目归属字段 (如果有必要)
    canvases = db.query(CanvasMetadata).filter(CanvasMetadata.project_id == "default", CanvasMetadata.owner_id == user_id).all()
    for c in canvases:
        filepath = get_canvas_file_path(user_id, c.id)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data["project"] = "default"
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
                
    db.delete(proj)
    db.commit()
    return True


# ==================== CANVAS CRUD ====================

def create_canvas_for_user(db: Session, user_id: str, title: str, icon: str, kind: str, project_id: str = None, board_x: float = None, board_y: float = None) -> Dict[str, Any]:
    """为用户创建新画布"""
    get_or_create_default_project(db, user_id)
    
    pid = str(project_id or "").strip()
    if not pid or pid == "null" or pid == "undefined":
        pid = "default"
        
    canvas_id = uuid.uuid4().hex
    ts = int(datetime.datetime.utcnow().timestamp() * 1000)
    
    # 1. 保存元数据到 SQLite
    meta = CanvasMetadata(
        id=canvas_id,
        name=title[:80],
        project_id=pid,
        owner_id=user_id,
        kind=kind,
        is_deleted=False,
        created_at=datetime.datetime.utcfromtimestamp(ts / 1000)
    )
    db.add(meta)
    db.commit()
    db.refresh(meta)
    
    # 2. 写入物理 JSON 文件，内容为初始画布结构
    canvas_data = {
        "id": canvas_id,
        "title": title[:80],
        "icon": icon[:32],
        "kind": kind,
        "owner": "",
        "color": "",
        "pinned": False,
        "project": pid,
        "created_at": ts,
        "updated_at": ts,
        "nodes": [],
        "connections": [],
        "viewport": {"x": 0, "y": 0, "scale": 1},
    }
    if board_x is not None:
        canvas_data["board_x"] = float(board_x)
    if board_y is not None:
        canvas_data["board_y"] = float(board_y)
        
    filepath = get_canvas_file_path(user_id, canvas_id)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(canvas_data, f, ensure_ascii=False, indent=2)
        
    return canvas_data

def get_canvas_for_user(db: Session, user_id: str, canvas_id: str, include_deleted: bool = False) -> Dict[str, Any]:
    """加载用户的具体画布 JSON 内容"""
    meta = db.query(CanvasMetadata).filter(CanvasMetadata.id == canvas_id, CanvasMetadata.owner_id == user_id).first()
    if not meta:
        return None
        
    if meta.is_deleted and not include_deleted:
        return None
        
    filepath = get_canvas_file_path(user_id, canvas_id)
    if not os.path.exists(filepath):
        # 兜底：如果数据库记录存在但物理文件丢失，重新创建一个空画布
        canvas_data = {
            "id": canvas_id,
            "title": meta.name,
            "icon": "layers",
            "kind": meta.kind,
            "owner": "",
            "color": "",
            "pinned": False,
            "project": meta.project_id,
            "created_at": int(meta.created_at.timestamp() * 1000),
            "updated_at": int(meta.created_at.timestamp() * 1000),
            "nodes": [],
            "connections": [],
            "viewport": {"x": 0, "y": 0, "scale": 1},
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(canvas_data, f, ensure_ascii=False, indent=2)
        return canvas_data
        
    with open(filepath, 'r', encoding='utf-8') as f:
        canvas_data = json.load(f)
        
    # 同步元数据状态以防不一致
    canvas_data["project"] = meta.project_id
    if meta.is_deleted:
        canvas_data["deleted_at"] = int(meta.updated_at.timestamp() * 1000)
    else:
        canvas_data.pop("deleted_at", None)
        
    return canvas_data

def save_canvas_for_user(db: Session, user_id: str, canvas_id: str, canvas_data: Dict[str, Any]) -> Dict[str, Any]:
    """保存画布 JSON 文件并更新 SQLite 元数据更新时间"""
    meta = db.query(CanvasMetadata).filter(CanvasMetadata.id == canvas_id, CanvasMetadata.owner_id == user_id).first()
    if not meta:
        return None
        
    ts = int(datetime.datetime.utcnow().timestamp() * 1000)
    canvas_data["updated_at"] = ts
    canvas_data["id"] = canvas_id
    
    # 更新 SQLite
    meta.updated_at = datetime.datetime.utcfromtimestamp(ts / 1000)
    if "title" in canvas_data:
        meta.name = canvas_data["title"][:80]
    db.commit()
    
    # 写入物理文件
    filepath = get_canvas_file_path(user_id, canvas_id)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(canvas_data, f, ensure_ascii=False, indent=2)
        
    return canvas_data

def update_canvas_meta_for_user(db: Session, user_id: str, canvas_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """快捷更新画布的元数据 (不改变 nodes/connections，也不更新全局 updated_at，不影响置顶排序)"""
    meta = db.query(CanvasMetadata).filter(CanvasMetadata.id == canvas_id, CanvasMetadata.owner_id == user_id).first()
    if not meta:
        return None
        
    # 读取物理文件
    canvas = get_canvas_for_user(db, user_id, canvas_id, include_deleted=True)
    if not canvas:
        return None
        
    if "title" in updates and updates["title"] is not None:
        title = updates["title"][:80]
        meta.name = title
        canvas["title"] = title
    if "icon" in updates and updates["icon"] is not None:
        canvas["icon"] = updates["icon"][:32]
    if "owner" in updates and updates["owner"] is not None:
        canvas["owner"] = str(updates["owner"])[:40]
    if "color" in updates and updates["color"] is not None:
        canvas["color"] = str(updates["color"])[:20]
    if "pinned" in updates and updates["pinned"] is not None:
        canvas["pinned"] = bool(updates["pinned"])
    if "project" in updates and updates["project"] is not None:
        pid = str(updates["project"]).strip() or "default"
        meta.project_id = pid
        canvas["project"] = pid
    if "board_x" in updates and updates["board_x"] is not None:
        canvas["board_x"] = float(updates["board_x"])
    if "board_y" in updates and updates["board_y"] is not None:
        canvas["board_y"] = float(updates["board_y"])
        
    db.commit()
    
    # 写回物理文件
    filepath = get_canvas_file_path(user_id, canvas_id)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(canvas, f, ensure_ascii=False, indent=2)
        
    # 返回精简版记录
    return {
        "id": canvas["id"],
        "title": canvas["title"],
        "icon": canvas["icon"],
        "kind": canvas["kind"],
        "owner": canvas.get("owner", ""),
        "color": canvas.get("color", ""),
        "pinned": canvas.get("pinned", False),
        "project": canvas.get("project", "default"),
        "created_at": canvas["created_at"],
        "updated_at": canvas["updated_at"],
        "deleted_at": canvas.get("deleted_at")
    }

def list_canvases_for_user(db: Session, user_id: str, is_deleted: bool = False) -> List[Dict[str, Any]]:
    """列出当前用户的所有画布，支持过滤回收站状态"""
    canvases = db.query(CanvasMetadata).filter(
        CanvasMetadata.owner_id == user_id, 
        CanvasMetadata.is_deleted == is_deleted
    ).all()
    
    out = []
    for c in canvases:
        # 加载轻量化元数据
        filepath = get_canvas_file_path(user_id, c.id)
        pinned = False
        icon = "layers"
        color = ""
        owner = ""
        created_at_ms = int(c.created_at.timestamp() * 1000)
        updated_at_ms = int(c.updated_at.timestamp() * 1000)
        
        # 尝试读取物理文件的部分字段，若丢失则用 DB 字段兜底
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                pinned = bool(data.get("pinned"))
                icon = data.get("icon", "layers")
                color = data.get("color", "")
                owner = data.get("owner", "")
                created_at_ms = data.get("created_at") or created_at_ms
                updated_at_ms = data.get("updated_at") or updated_at_ms
            except Exception:
                pass
                
        rec = {
            "id": c.id,
            "title": c.name,
            "icon": icon,
            "kind": c.kind,
            "owner": owner,
            "color": color,
            "pinned": pinned,
            "project": c.project_id,
            "created_at": created_at_ms,
            "updated_at": updated_at_ms,
        }
        if is_deleted:
            rec["deleted_at"] = updated_at_ms
        out.append(rec)
        
    # 排序：置顶(pinned)在最前，之后按 updated_at 倒序
    if is_deleted:
        return sorted(out, key=lambda item: item["deleted_at"], reverse=True)
    else:
        return sorted(out, key=lambda item: (0 if item["pinned"] else 1, -item["updated_at"]))

def delete_canvas_for_user(db: Session, user_id: str, canvas_id: str) -> bool:
    """将画布移入回收站"""
    meta = db.query(CanvasMetadata).filter(CanvasMetadata.id == canvas_id, CanvasMetadata.owner_id == user_id).first()
    if not meta or meta.is_deleted:
        return False
        
    meta.is_deleted = True
    meta.updated_at = datetime.datetime.utcnow()
    db.commit()
    
    # 物理文件的 deleted_at 同步
    canvas = get_canvas_for_user(db, user_id, canvas_id, include_deleted=True)
    if canvas:
        canvas["deleted_at"] = int(meta.updated_at.timestamp() * 1000)
        filepath = get_canvas_file_path(user_id, canvas_id)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(canvas, f, ensure_ascii=False, indent=2)
            
    return True

def restore_canvas_for_user(db: Session, user_id: str, canvas_id: str) -> Dict[str, Any]:
    """从回收站中恢复画布"""
    meta = db.query(CanvasMetadata).filter(CanvasMetadata.id == canvas_id, CanvasMetadata.owner_id == user_id).first()
    if not meta or not meta.is_deleted:
        return None
        
    meta.is_deleted = False
    meta.updated_at = datetime.datetime.utcnow()
    db.commit()
    
    # 物理文件清除 deleted_at
    canvas = get_canvas_for_user(db, user_id, canvas_id, include_deleted=False)
    if canvas:
        canvas.pop("deleted_at", None)
        filepath = get_canvas_file_path(user_id, canvas_id)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(canvas, f, ensure_ascii=False, indent=2)
            
    return canvas

def purge_canvas_permanently_for_user(db: Session, user_id: str, canvas_id: str) -> bool:
    """物理删除画布（彻底清除）"""
    meta = db.query(CanvasMetadata).filter(CanvasMetadata.id == canvas_id, CanvasMetadata.owner_id == user_id).first()
    if not meta:
        return False
        
    db.delete(meta)
    db.commit()
    
    # 物理删除文件
    filepath = get_canvas_file_path(user_id, canvas_id)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass
            
    return True
