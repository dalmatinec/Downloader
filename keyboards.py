# keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any
import json


class KeyboardBuilder:
    """Универсальный построитель клавиатур из базы данных"""
    
    @staticmethod
    def build_reply(buttons: List[Dict[str, Any]]) -> ReplyKeyboardMarkup:
        """
        Строит ReplyKeyboardMarkup из списка кнопок из БД
        buttons: список с полями: text, row_num, order_num
        """
        if not buttons:
            return ReplyKeyboardMarkup(resize_keyboard=True)
        
        # Фильтруем только активные кнопки
        active_buttons = [b for b in buttons if b.get("is_active", 1) == 1]
        
        if not active_buttons:
            return ReplyKeyboardMarkup(resize_keyboard=True)
        
        # Группируем по row_num
        rows_dict = {}
        for btn in active_buttons:
            row = btn.get("row_num", 0)
            if row not in rows_dict:
                rows_dict[row] = []
            rows_dict[row].append(btn)
        
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        
        # Сортируем ряды по row_num
        for row_num in sorted(rows_dict.keys()):
            # Сортируем кнопки в ряду по order_num
            sorted_buttons = sorted(rows_dict[row_num], key=lambda x: x.get("order_num", 0))
            row_buttons = [KeyboardButton(btn["text"]) for btn in sorted_buttons]
            keyboard.row(*row_buttons)
        
        return keyboard
    
    @staticmethod
    def build_inline(buttons: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
        """
        Строит InlineKeyboardMarkup из списка кнопок из БД
        buttons: список с полями: text, action_type_id, action_data, row_num, order_num
        """
        if not buttons:
            return InlineKeyboardMarkup()
        
        # Фильтруем только активные кнопки
        active_buttons = [b for b in buttons if b.get("is_active", 1) == 1]
        
        if not active_buttons:
            return InlineKeyboardMarkup()
        
        # Группируем по row_num
        rows_dict = {}
        for btn in active_buttons:
            row = btn.get("row_num", 0)
            if row not in rows_dict:
                rows_dict[row] = []
            rows_dict[row].append(btn)
        
        keyboard = InlineKeyboardMarkup()
        
        # Сортируем ряды по row_num
        for row_num in sorted(rows_dict.keys()):
            # Сортируем кнопки в ряду по order_num
            sorted_buttons = sorted(rows_dict[row_num], key=lambda x: x.get("order_num", 0))
            
            row_buttons = []
            for btn in sorted_buttons:
                action_type = btn.get("action_type_id", "")
                action_data = btn.get("action_data", {})
                
                # По action_type_id определяем тип кнопки
                if action_type == "url":
                    row_buttons.append(InlineKeyboardButton(
                        text=btn["text"],
                        url=action_data.get("url", "#")
                    ))
                elif action_type == "callback":
                    row_buttons.append(InlineKeyboardButton(
                        text=btn["text"],
                        callback_data=action_data.get("callback_data", btn["id"])
                    ))
                elif action_type == "switch_inline":
                    row_buttons.append(InlineKeyboardButton(
                        text=btn["text"],
                        switch_inline_query=action_data.get("query", "")
                    ))
                else:
                    # По умолчанию callback
                    row_buttons.append(InlineKeyboardButton(
                        text=btn["text"],
                        callback_data=btn["id"]
                    ))
            
            keyboard.row(*row_buttons)
        
        return keyboard
    
    @staticmethod
    def from_db(buttons: List[Dict[str, Any]], is_reply: bool = False) -> Any:
        """Универсальный метод построения из БД"""
        if is_reply:
            return KeyboardBuilder.build_reply(buttons)
        return KeyboardBuilder.build_inline(buttons)