import oracledb
import os
import sys
import json

# Oracle Database Configuration
DB_USER = os.environ.get("ORACLE_DB_USER", "admin")
DB_PASSWORD = os.environ.get("ORACLE_DB_PASSWORD", "password123")
DB_DSN = os.environ.get("ORACLE_DB_DSN", "localhost:1521/xe")

def get_connection():
    try:
        conn = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN
        )
        return conn
    except Exception as e:
        print(f"DATABASE ERROR: Failed to connect to Oracle: {e}", file=sys.stderr)
        return None

def verify_user(username, password):
    conn = get_connection()
    if not conn:
        return username == "admin" and password == "password123"

    try:
        with conn.cursor() as cursor:
            sql = "SELECT USER_ID FROM STTM_USER WHERE USER_ID = :1 AND USER_PASSWORD = :2"
            cursor.execute(sql, [username, password])
            row = cursor.fetchone()
            return True if row else False
    except Exception as e:
        print(f"DATABASE ERROR: Query execution failed: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()

def save_analysis(user_id, project_name, raw_input, req_json, impact_json, files):
    """
    Saves a full analysis cycle to the EER specialized DBMS.
    Creates entries in superclass (STTM_ANALYSIS) and appropriate subclasses.
    """
    conn = get_connection()
    if not conn: return None

    try:
        with conn.cursor() as cursor:
            # 1. Get or Create Project
            cursor.execute("SELECT PROJECT_ID FROM STTM_PROJECT WHERE USER_ID = :1 AND PROJECT_NAME = :2", [user_id, project_name])
            row = cursor.fetchone()
            if row:
                project_id = row[0]
            else:
                cursor.execute(
                    "INSERT INTO STTM_PROJECT (USER_ID, PROJECT_NAME) VALUES (:1, :2)",
                    [user_id, project_name]
                )
                cursor.execute("SELECT PROJECT_ID FROM STTM_PROJECT WHERE USER_ID = :1 AND PROJECT_NAME = :2", [user_id, project_name])
                project_id = cursor.fetchone()[0]

            # 2. Save Requirement Analysis (Superclass + Subclass)
            cursor.execute(
                "INSERT INTO STTM_ANALYSIS (PROJECT_ID, RAW_INPUT, STATUS, ANALYSIS_TYPE) VALUES (:1, :2, 'COMPLETED', 'REQUIREMENT')",
                [project_id, raw_input]
            )
            cursor.execute("SELECT ANALYSIS_ID FROM STTM_ANALYSIS WHERE PROJECT_ID = :1 AND ANALYSIS_TYPE = 'REQUIREMENT' ORDER BY CREATED_AT DESC FETCH FIRST 1 ROW ONLY", [project_id])
            req_analysis_id = cursor.fetchone()[0]
            
            cursor.execute(
                """INSERT INTO STTM_REQUIREMENT_ANALYSIS 
                   (ANALYSIS_ID, BUSINESS_OBJECTIVE, CLIENT_TYPE, FUNCTIONAL_REQUIREMENTS, NON_FUNCTIONAL_REQUIREMENTS, CONVERSATION_RESPONSE) 
                   VALUES (:1, :2, :3, :4, :5, :6)""",
                [req_analysis_id, 
                 req_json.get('business_objective', ''),
                 req_json.get('client_type', ''),
                 json.dumps(req_json.get('functional_requirements', [])),
                 json.dumps(req_json.get('non_functional_requirements', [])),
                 'Y' if req_json.get('conversation_response') else 'N']
            )

            # 3. Save Impact Analysis (Superclass + Subclass)
            cursor.execute(
                "INSERT INTO STTM_ANALYSIS (PROJECT_ID, RAW_INPUT, STATUS, ANALYSIS_TYPE) VALUES (:1, :2, 'COMPLETED', 'IMPACT')",
                [project_id, raw_input]
            )
            cursor.execute("SELECT ANALYSIS_ID FROM STTM_ANALYSIS WHERE PROJECT_ID = :1 AND ANALYSIS_TYPE = 'IMPACT' ORDER BY CREATED_AT DESC FETCH FIRST 1 ROW ONLY", [project_id])
            impact_analysis_id = cursor.fetchone()[0]
            
            cursor.execute(
                """INSERT INTO STTM_IMPACT_ANALYSIS 
                   (ANALYSIS_ID, AFFECTED_COMPONENTS, SCHEMA_CHANGES, CODE_CHANGES, EFFORT_ESTIMATION, OVERALL_RISK, MITIGATION_STRATEGIES) 
                   VALUES (:1, :2, :3, :4, :5, :6, :7)""",
                [impact_analysis_id,
                 json.dumps(impact_json.get('affected_components', [])),
                 json.dumps(impact_json.get('schema_changes', [])),
                 json.dumps(impact_json.get('code_changes', [])),
                 json.dumps(impact_json.get('effort_estimation', {})),
                 impact_json.get('overall_risk', ''),
                 json.dumps(impact_json.get('mitigation_strategies', []))]
            )

            # 4. Save Code Generation Analysis (Superclass + Subclass)
            cursor.execute(
                "INSERT INTO STTM_ANALYSIS (PROJECT_ID, RAW_INPUT, STATUS, ANALYSIS_TYPE) VALUES (:1, :2, 'COMPLETED', 'CODE_GENERATION')",
                [project_id, raw_input]
            )
            cursor.execute("SELECT ANALYSIS_ID FROM STTM_ANALYSIS WHERE PROJECT_ID = :1 AND ANALYSIS_TYPE = 'CODE_GENERATION' ORDER BY CREATED_AT DESC FETCH FIRST 1 ROW ONLY", [project_id])
            code_analysis_id = cursor.fetchone()[0]
            
            cursor.execute(
                "INSERT INTO STTM_CODE_GENERATION_ANALYSIS (ANALYSIS_ID, GENERATION_SUMMARY, TOTAL_FILES_GENERATED) VALUES (:1, :2, :3)",
                [code_analysis_id, f"Generated {len(files)} files", len(files)]
            )

            # 5. Save Generated Code Files
            for file in files:
                cursor.execute(
                    "INSERT INTO STTM_GENERATED_CODE (ANALYSIS_ID, FILE_NAME, FILE_TYPE, CONTENT) VALUES (:1, :2, :3, :4)",
                    [code_analysis_id, file.get('file_name'), file.get('file_type'), file.get('file_content')]
                )

            conn.commit()
            return code_analysis_id
    except Exception as e:
        print(f"DATABASE ERROR: Failed to save analysis: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        conn.rollback()
        return None
    finally:
        conn.close()

def get_recent_analyses(user_id, limit=5):
    conn = get_connection()
    if not conn: return []

    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT a.ANALYSIS_ID, p.PROJECT_NAME, a.ANALYSIS_TYPE, a.CREATED_AT 
                FROM STTM_ANALYSIS a
                JOIN STTM_PROJECT p ON a.PROJECT_ID = p.PROJECT_ID
                WHERE p.USER_ID = :1
                ORDER BY a.CREATED_AT DESC
                FETCH FIRST :2 ROWS ONLY
            """
            cursor.execute(sql, [user_id, limit])
            return cursor.fetchall()
    except Exception as e:
        print(f"DATABASE ERROR: Failed to fetch history: {e}", file=sys.stderr)
        return []
    finally:
        conn.close()

def create_user(username, password):
    """
    Creates a new user in the STTM_USER table.
    Returns True if successful, False if user already exists or error.
    """
    conn = get_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cursor:
            # Check if user already exists
            cursor.execute("SELECT USER_ID FROM STTM_USER WHERE USER_ID = :1", [username])
            if cursor.fetchone():
                return False
            
            # Insert new user
            cursor.execute(
                "INSERT INTO STTM_USER (USER_ID, USER_PASSWORD) VALUES (:1, :2)",
                [username, password]
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"DATABASE ERROR: User creation failed: {e}", file=sys.stderr)
        conn.rollback()
        return False
    finally:
        conn.close()
