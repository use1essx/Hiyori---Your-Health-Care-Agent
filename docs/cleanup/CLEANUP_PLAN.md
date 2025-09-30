# 🧹 HEALTHCARE AI REPOSITORY CLEANUP PLAN

**Generated:** December 2024  
**Repository:** `/workspaces/fyp2526-use1essx/healthcare_ai_live2d_unified`  
**Current Stats:** 219 files, 15MB total size

## 📊 REPOSITORY METRICS (BEFORE)

- **Total Files:** 219
- **Repository Size:** 15MB
- **Python Files:** 104
- **HTML Files:** 19
- **JSON Files:** 32
- **Modified Files:** 1 (git status)
- **Large Files (>1MB):** 4 Live2D texture files

## 🔍 FILE IMPACT TABLE

| Path | Action | Reason | Risk | Follow-up |
|------|--------|--------|------|-----------|
| `src/web/live2d/backend/requirements.txt` | DELETE | Duplicate of root requirements.txt | Low | Update any references to use root file |
| `scripts/pgadmin/backup_automation.py` | KEEP | Named as backup but appears to be functional | Low | Review for actual usage |
| `src/web/live2d/frontend/Resources/Haru/motions/Hiyori_*.motion3.json` | REVIEW | Hiyori motion files in Haru directory - naming mismatch | Medium | Verify correct character assignments |
| `config/pgadmin/config_local.py` | KEEP | Active configuration file | Low | None |
| Multiple `__init__.py` (26 files) | KEEP | Required for Python package structure | Low | None |
| Multiple `README.md` (4 files) | MERGE | Consolidate documentation | Low | Merge content into main README |
| `routes.py` files (3 instances) | KEEP | Different modules, legitimate separation | Low | None |
| Empty `__init__.py` files (10 files) | KEEP | Required for Python imports | Low | None |

## 🔄 DUPLICATION MAP

### 1. Requirements Files
- **Canonical:** `requirements.txt` (root)
- **Duplicates:** `src/web/live2d/backend/requirements.txt`
- **Action:** Delete duplicate, ensure all references point to root

### 2. README Files
- **Canonical:** `README.md` (root)
- **Duplicates:** 
  - `docs/README.md`
  - `scripts/README.md`
  - `tools/README.md`
- **Action:** Merge relevant content into main README, delete duplicates

### 3. Live2D Motion Files (Naming Issue)
- **Issue:** Hiyori motion files located in Haru character directory
- **Files:** `src/web/live2d/frontend/Resources/Haru/motions/Hiyori_m*.motion3.json`
- **Action:** Move to correct Hiyori directory or rename if intended for Haru

### 4. Security Modules
- **Files:** 2 instances of `security.py`
- **Locations:** `src/core/security.py`, `src/web/security.py`
- **Action:** Keep both (different purposes - core vs web security)

## 🗑️ USELESS FILE HEURISTICS APPLIED

### Applied Heuristics:
1. ✅ **Generated caches/temp files:** None found
2. ✅ **Obvious leftovers:** Found `backup_automation.py` (keeping as functional)
3. ✅ **Orphaned assets:** No orphaned images found
4. ✅ **Unused modules:** All Python files compile successfully
5. ✅ **Old migrations:** All appear current
6. ✅ **Redundant configs:** Found duplicate requirements.txt
7. ✅ **README duplicates:** Found 4 README files

### Files Identified for Removal:
- `src/web/live2d/backend/requirements.txt` (duplicate)
- Potential consolidation of README files

## 🎯 PROPOSED IMPROVEMENTS

### 1. Structure Optimizations
- Consolidate documentation into main README
- Remove duplicate requirements file
- Fix Live2D character/motion file organization

### 2. Dependency Management
- **Current:** Multiple requirements files
- **Proposed:** Single source of truth in root `requirements.txt`
- **Benefit:** Simplified dependency management

### 3. Documentation Consolidation
- **Current:** 4 separate README files
- **Proposed:** Single comprehensive README with sections
- **Benefit:** Centralized documentation

### 4. Asset Organization
- **Issue:** Motion files for Hiyori character in Haru directory
- **Proposed:** Correct file organization by character
- **Benefit:** Logical asset structure

## ⚠️ RISK ASSESSMENT

### Low Risk Changes:
- Removing duplicate requirements.txt
- Consolidating README files
- Documentation updates

### Medium Risk Changes:
- Moving Live2D motion files (could break character animations)
- Any import path changes

### High Risk Changes:
- None identified in this cleanup

## 📋 DEPENDENCIES ANALYSIS

### Current Dependencies:
- **Root requirements.txt:** 91 lines (comprehensive)
- **Duplicate requirements.txt:** Smaller subset
- **pyproject.toml:** Modern Python project configuration

### Recommendation:
- Keep root `requirements.txt` as canonical
- Remove duplicate in `src/web/live2d/backend/`
- Maintain `pyproject.toml` for modern Python tooling

## 🧪 TESTING REQUIREMENTS

### Pre-Cleanup Tests:
- ✅ All services running (confirmed)
- ✅ Authentication working (confirmed)
- ✅ Profile endpoint working (confirmed)
- ✅ Demo users functional (confirmed)

### Post-Cleanup Verification:
1. Verify all services still start
2. Test authentication flow
3. Verify Live2D character animations work
4. Check that all imports resolve correctly

## 📈 EXPECTED IMPROVEMENTS

### File Count Reduction:
- **Before:** 219 files
- **After:** ~215 files (-4 README duplicates)

### Documentation Quality:
- **Before:** Fragmented across multiple files
- **After:** Consolidated, comprehensive documentation

### Maintenance Burden:
- **Before:** Multiple requirements files to maintain
- **After:** Single source of truth for dependencies

## 🎯 NEXT STEPS

1. **Review this plan** for approval
2. **Generate PATCH** with specific changes
3. **Create DEPRECATIONS.md** for removed items
4. **Update CHANGELOG.md** with changes
5. **Execute cleanup** with verification steps

## 🔒 SAFETY MEASURES

- All changes are reversible via git
- No critical system files affected
- No breaking changes to API endpoints
- Preserve all functional code and configurations
- Maintain backward compatibility for imports

---

**Cleanup Philosophy:** Conservative approach focusing on clear duplicates and organizational improvements while preserving all functional code and maintaining system stability.
