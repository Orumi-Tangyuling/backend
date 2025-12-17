import pytest
from unittest.mock import patch, Mock
from datetime import datetime
import sys
import os

# 상위 디렉토리의 api 모듈을 import하기 위해 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fetch.fetchers import fetch_current


class TestCurrent:
    @pytest.fixture
    def sample_date(self):
        """테스트용 날짜 fixture"""
        return datetime(2016, 1, 5, 15, 20, 0)
    
    @pytest.fixture
    def sample_response(self):
        """정상 응답 데이터"""
        return {
            "result": {
                "data": [
                    {"current_dir": "143", "current_speed": "5.0", "pre_lon": "122.09167", "pre_lat": "36.93889"},
                    {"current_dir": "20", "current_speed": "59.0", "pre_lon": "122.63333", "pre_lat": "36.93889"},
                    {"current_dir": "16", "current_speed": "52.0", "pre_lon": "122.74167", "pre_lat": "36.93889"}
                ],
                "meta": {
                    "obs_last_req_cnt": "800/20000",
                    "sch_time": "2016-01-05 15:20",
                    "sch_minX": "122",
                    "sch_maxX": "126",
                    "sch_minY": "32",
                    "sch_maxY": "37"
                }
            }
        }
    
    @patch('api.fetchers.requests.get')
    @patch.dict(os.environ, {'API_KEY': 'test_api_key'})
    def test_current_success(self, mock_get, sample_date, sample_response):
        """정상적으로 평균값을 반환하는 케이스"""
        # Mock 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_response
        mock_get.return_value = mock_response
        
        # 함수 실행
        avg_dir, avg_speed = fetch_current(sample_date, 36.5, 124.3)
        
        # 검증
        expected_dir = (143 + 20 + 16) / 3
        expected_speed = (5.0 + 59.0 + 52.0) / 3
        
        assert avg_dir == pytest.approx(expected_dir)
        assert avg_speed == pytest.approx(expected_speed)
        
        # API 호출 파라미터 검증
        call_args = mock_get.call_args
        params = call_args[1]['params']
        assert params['Date'] == '20160105'
        assert params['Hour'] == '15'
        assert params['Minute'] == '20'
        assert params['MinY'] == 36
        assert params['MaxY'] == 37
        assert params['MinX'] == 124
        assert params['MaxX'] == 125
    
    @patch('api.fetchers.requests.get')
    @patch.dict(os.environ, {'API_KEY': 'test_api_key'})
    def test_current_api_failure(self, mock_get, sample_date):
        """API 요청 실패 케이스"""
        # Mock 설정 - 500 에러
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # 예외 발생 확인
        with pytest.raises(Exception) as exc_info:
            fetch_current(sample_date, 36.5, 124.3)
        
        assert "API 요청 실패: 500" in str(exc_info.value)
    
    @patch('api.fetchers.requests.get')
    @patch.dict(os.environ, {'API_KEY': 'test_api_key'})
    def test_current_json_parse_error(self, mock_get, sample_date):
        """JSON 파싱 실패 케이스"""
        # Mock 설정 - 잘못된 JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Invalid JSON response"
        mock_get.return_value = mock_response
        
        # 예외 발생 확인
        with pytest.raises(Exception) as exc_info:
            fetch_current(sample_date, 36.5, 124.3)
        
        assert "JSON 파싱 실패" in str(exc_info.value)
    
    @patch('api.fetchers.requests.get')
    @patch.dict(os.environ, {'API_KEY': 'test_api_key'})
    def test_current_invalid_response_format(self, mock_get, sample_date):
        """응답 데이터 형식이 올바르지 않은 케이스"""
        # Mock 설정 - result 키가 없는 응답
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "No data"}
        mock_get.return_value = mock_response
        
        # 예외 발생 확인
        with pytest.raises(Exception) as exc_info:
            fetch_current(sample_date, 36.5, 124.3)
        
        assert "응답 데이터 형식이 올바르지 않습니다" in str(exc_info.value)
    
    @patch('api.fetchers.requests.get')
    @patch.dict(os.environ, {'API_KEY': 'test_api_key'})
    def test_current_no_valid_data(self, mock_get, sample_date):
        """유효한 데이터가 없는 케이스"""
        # Mock 설정 - 빈 data 배열
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "data": []
            }
        }
        mock_get.return_value = mock_response
        
        # 예외 발생 확인
        with pytest.raises(Exception) as exc_info:
            fetch_current(sample_date, 36.5, 124.3)
        
        assert "유효한 데이터가 없습니다" in str(exc_info.value)
    
    @patch('api.fetchers.requests.get')
    @patch.dict(os.environ, {'API_KEY': 'test_api_key'})
    def test_current_missing_fields(self, mock_get, sample_date):
        """일부 데이터에 필드가 누락된 케이스"""
        # Mock 설정 - 일부 데이터만 유효
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "data": [
                    {"current_dir": "100", "current_speed": "10.0"},
                    {"current_dir": "200"},  # current_speed 누락
                    {"current_speed": "30.0"},  # current_dir 누락
                    {"current_dir": "300", "current_speed": "50.0"}
                ]
            }
        }
        mock_get.return_value = mock_response
        
        # 함수 실행
        avg_dir, avg_speed = fetch_current(sample_date, 36.5, 124.3)
        
        # 유효한 데이터만 계산 (첫 번째와 네 번째 데이터)
        expected_dir = (100 + 300) / 2
        expected_speed = (10.0 + 50.0) / 2
        
        assert avg_dir == pytest.approx(expected_dir)
        assert avg_speed == pytest.approx(expected_speed)
    
    @patch('api.fetchers.requests.get')
    @patch.dict(os.environ, {'API_KEY': 'test_api_key'})
    def test_current_floor_ceil_calculation(self, mock_get, sample_date, sample_response):
        """위도/경도의 내림/올림 계산 검증"""
        mock_response_obj = Mock()
        mock_response_obj.status_code = 200
        mock_response_obj.json.return_value = sample_response
        mock_get.return_value = mock_response_obj
        
        # 36.5는 36(floor), 37(ceil)
        # 124.3은 124(floor), 125(ceil)
        fetch_current(sample_date, 36.5, 124.3)
        
        params = mock_get.call_args[1]['params']
        assert params['MinY'] == 36
        assert params['MaxY'] == 37
        assert params['MinX'] == 124
        assert params['MaxX'] == 125
