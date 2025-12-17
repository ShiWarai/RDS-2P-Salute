"""
Сервис управления привязками пользователей к роботам
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

CODE_EXPIRY_SECONDS = 300  # 5 минут


class BindingService:
    """Управление привязками пользователей к роботам"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Инициализация сервиса привязок
        
        Args:
            data_dir: Директория для хранения данных (по умолчанию data/ в корне проекта)
        """
        if data_dir is None:
            # Определяем корень проекта (на 2 уровня выше от app/services/)
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data"
        
        data_dir.mkdir(exist_ok=True)
        
        self.bindings_file = data_dir / "user_robot_bindings.json"
        self.states_file = data_dir / "binding_states.json"
        self._bindings: Dict[str, str] = {}
        self._binding_states: Dict[str, Dict[str, Any]] = {}
        self._load_bindings()
        self._load_states()
    
    def _load_bindings(self):
        """Загружает постоянные привязки из файла"""
        if self.bindings_file.exists():
            try:
                with open(self.bindings_file, 'r', encoding='utf-8') as f:
                    self._bindings = json.load(f)
                logger.info(f"Loaded {len(self._bindings)} user-robot bindings")
            except Exception as e:
                logger.error(f"Error loading bindings: {e}")
                self._bindings = {}
        else:
            self._bindings = {}
            self._save_bindings()
    
    def _save_bindings(self):
        """Сохраняет постоянные привязки в файл"""
        try:
            with open(self.bindings_file, 'w', encoding='utf-8') as f:
                json.dump(self._bindings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving bindings: {e}")
    
    def _load_states(self):
        """Загружает временные состояния привязки из файла"""
        if self.states_file.exists():
            try:
                with open(self.states_file, 'r', encoding='utf-8') as f:
                    self._binding_states = json.load(f)
                logger.info(f"Loaded {len(self._binding_states)} binding states")
            except Exception as e:
                logger.error(f"Error loading binding states: {e}")
                self._binding_states = {}
        else:
            self._binding_states = {}
            self._save_states()
    
    def _save_states(self):
        """Сохраняет временные состояния привязки в файл"""
        try:
            with open(self.states_file, 'w', encoding='utf-8') as f:
                json.dump(self._binding_states, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving binding states: {e}")
    
    def get_user_id(self, uuid_data: Dict[str, Any]) -> Optional[str]:
        """
        Извлекает идентификатор пользователя из uuid
        
        Args:
            uuid_data: Объект uuid из запроса SmartApp API
            
        Returns:
            Идентификатор пользователя (sub или userId)
        """
        # Используем sub как основной идентификатор (более стабильный)
        user_id = uuid_data.get("sub") or uuid_data.get("userId")
        return user_id
    
    def has_binding(self, user_id: str) -> bool:
        """Проверяет, есть ли постоянная привязка для пользователя"""
        return user_id in self._bindings
    
    def get_robot_id(self, user_id: str) -> Optional[str]:
        """Получает ID привязанного робота для пользователя"""
        return self._bindings.get(user_id)
    
    def get_binding_state(self, user_id: str) -> Optional[str]:
        """Получает текущее состояние процесса привязки"""
        if user_id not in self._binding_states:
            logger.debug(f"User {user_id} not in binding_states")
            return None
        
        state = self._binding_states[user_id]
        
        # Проверяем, не истек ли код
        expires_at = state.get("expires_at", 0)
        current_time = time.time()
        logger.debug(f"Checking binding state for user {user_id}: expires_at={expires_at}, current_time={current_time}, diff={current_time - expires_at}")
        if current_time > expires_at:
            logger.info(f"Binding code expired for user {user_id}")
            self.cancel_binding(user_id)
            return None
        
        return "waiting_code"
    
    def start_binding(self, user_id: str, robot_id: str, code: str, expires_at: float) -> bool:
        """Начинает процесс привязки - сохраняет состояние ожидания кода"""
        if not user_id or not robot_id or not code:
            logger.error("User ID, robot ID and code are required for binding")
            return False
        
        # Приводим код к строке и убираем пробелы
        code_str = str(code).strip()
        logger.debug(f"Сохранение кода привязки: '{code_str}' (type: {type(code_str).__name__})")
        
        self._binding_states[user_id] = {
            "robot_id": robot_id,
            "code": code_str,
            "expires_at": expires_at,
            "attempts": 0,
            "created_at": time.time()
        }
        self._save_states()
        logger.info(f"Started binding process for user {user_id} to robot {robot_id}")
        return True
    
    def verify_binding_code(self, user_id: str, code: str) -> tuple[bool, str]:
        """Проверяет код верификации"""
        if user_id not in self._binding_states:
            return False, "Процесс привязки не начат"
        
        state = self._binding_states[user_id]
        
        # Проверяем истечение времени
        expires_at = state.get("expires_at", 0)
        if time.time() > expires_at:
            self.cancel_binding(user_id)
            return False, "Код истек. Начните привязку заново."
        
        # Проверяем код
        stored_code = state.get("code", "")
        logger.debug(f"Проверка кода: введённый='{code}' (type: {type(code).__name__}), сохранённый='{stored_code}' (type: {type(stored_code).__name__})")
        # Приводим оба кода к строкам для сравнения
        code_str = str(code).strip()
        stored_code_str = str(stored_code).strip()
        if code_str != stored_code_str:
            # Увеличиваем счетчик попыток
            state["attempts"] = state.get("attempts", 0) + 1
            self._save_states()
            
            attempts = state["attempts"]
            if attempts >= 3:
                self.cancel_binding(user_id)
                return False, "Превышено количество попыток. Начните привязку заново."
            else:
                remaining = 3 - attempts
                return False, f"Неверный код. Осталось попыток: {remaining}"
        
        # Код верный
        return True, "Код подтвержден"
    
    def complete_binding(self, user_id: str) -> bool:
        """Завершает привязку - сохраняет постоянную привязку"""
        if user_id not in self._binding_states:
            logger.error(f"No binding state found for user {user_id}")
            return False
        
        state = self._binding_states[user_id]
        robot_id = state.get("robot_id")
        
        if not robot_id:
            logger.error(f"No robot_id in binding state for user {user_id}")
            return False
        
        # Сохраняем постоянную привязку
        self._bindings[user_id] = robot_id
        self._save_bindings()
        
        # Очищаем временное состояние
        del self._binding_states[user_id]
        self._save_states()
        
        logger.info(f"Completed binding: user {user_id} -> robot {robot_id}")
        return True
    
    def cancel_binding(self, user_id: str) -> bool:
        """Отменяет процесс привязки"""
        if user_id in self._binding_states:
            del self._binding_states[user_id]
            self._save_states()
            logger.info(f"Cancelled binding for user {user_id}")
            return True
        return False
    
    def unbind_robot(self, user_id: str) -> bool:
        """Отвязывает робота от пользователя"""
        if user_id in self._bindings:
            del self._bindings[user_id]
            self._save_bindings()
            logger.info(f"Unbound robot from user {user_id}")
            return True
        return False
    
    def get_binding_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о состоянии привязки для пользователя"""
        # Проверяем постоянную привязку
        if user_id in self._bindings:
            return {
                "has_binding": True,
                "robot_id": self._bindings[user_id],
                "state": "completed"
            }
        
        # Проверяем временное состояние
        state = self.get_binding_state(user_id)
        if state == "waiting_code":
            binding_state = self._binding_states[user_id]
            return {
                "has_binding": False,
                "robot_id": binding_state.get("robot_id"),
                "state": "waiting_code",
                "attempts": binding_state.get("attempts", 0)
            }
        
        return {
            "has_binding": False,
            "state": None
        }


