"""
백그라운드 스케줄러 설정
매일 아침 6시에 해변 예측 데이터를 자동으로 수집합니다.
"""
import logging
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 스크립트 경로
BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPT_PATH = BASE_DIR / "scripts" / "populate_beach_predictions.py"


def collect_beach_predictions():
    """
    해변 예측 데이터 수집 작업
    오늘 날짜의 데이터를 생성합니다.
    """
    logger.info("=== 해변 예측 데이터 수집 시작 ===")
    start_time = datetime.now()
    
    # 오늘 날짜만 실행
    today = datetime.now().date()
    
    start_str = today.strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")
    
    logger.info(f"수집 기간: {start_str} ~ {end_str}")
    logger.info(f"스크립트 실행: {SCRIPT_PATH}")
    
    try:
        # Python 스크립트 실행
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--start", start_str, "--end", end_str],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=3600  # 1시간 타임아웃
        )
        
        # 출력 로깅
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logger.info(line)
        
        if result.returncode == 0:
            elapsed_time = datetime.now() - start_time
            logger.info("=" * 50)
            logger.info(f"데이터 수집 완료! (소요 시간: {elapsed_time})")
            logger.info("=" * 50)
        else:
            logger.error(f"스크립트 실행 실패 (exit code: {result.returncode})")
            if result.stderr:
                logger.error(f"에러: {result.stderr}")
                
    except subprocess.TimeoutExpired:
        logger.error("스크립트 실행 타임아웃 (1시간 초과)")
    except Exception as e:
        logger.error(f"스크립트 실행 중 오류 발생: {str(e)}")


# 스케줄러 인스턴스
scheduler = BackgroundScheduler()


def start_scheduler():
    """
    스케줄러 시작
    매일 아침 6시에 collect_beach_predictions 실행
    """
    # 매일 오전 6시에 실행
    scheduler.add_job(
        collect_beach_predictions,
        trigger=CronTrigger(hour=6, minute=0),
        id="beach_predictions_daily",
        name="해변 예측 데이터 수집",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✓ 스케줄러 시작됨 - 매일 오전 6시에 데이터 수집 실행")
    
    # 다음 실행 시간 출력
    job = scheduler.get_job("beach_predictions_daily")
    if job and job.next_run_time:
        logger.info(f"다음 실행 예정: {job.next_run_time}")


def stop_scheduler():
    """스케줄러 종료"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("스케줄러 종료됨")


def run_now():
    """
    수동으로 즉시 실행 (테스트용)
    """
    logger.info("수동 실행 요청")
    collect_beach_predictions()
