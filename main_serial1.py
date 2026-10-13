import numpy as np
import sys

from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt6.QtCore import QSize, Qt, QIODevice
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QRadioButton, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QGridLayout, QCheckBox, QGroupBox, QSlider, QMessageBox, QLabel, QComboBox, QPlainTextEdit

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("T-SPEX | BJT SPICE-parameters extractor")
        self.setFixedSize(520, 420)

        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        model_layout = QVBoxLayout()
        results_layout = QGridLayout()
        control_layout = QVBoxLayout()

        self.field_results = QGroupBox('Результаты измерений')
        self.field_control = QGroupBox('Управление комплексом')
        self.field_model = QGroupBox('SPICE-модель')

        self.combo_ports = QComboBox()

        self.input_model = QLineEdit()
        #self.input_model.setText('')
        self.input_logs = QPlainTextEdit()
        self.input_logs.setReadOnly(True)
        self.input_type = QLineEdit()
        self.input_pinout = QLineEdit()
        self.input_is = QLineEdit()
        self.input_bf = QLineEdit()
        self.input_nf = QLineEdit()
        self.input_rb = QLineEdit()
        self.input_ikf = QLineEdit()
        self.input_ise = QLineEdit()
        self.input_ne = QLineEdit()
        self.input_re = QLineEdit()
        self.input_rc = QLineEdit()

        self.text_connect = QLabel('Модуль: не подключен')
        self.text_description = QLabel('')
        self.text_type = QLabel('Тип транзистора')
        self.text_pinout = QLabel('Распиновка')
        self.text_is = QLabel('IS')
        self.text_bf = QLabel('BF')
        self.text_nf = QLabel('NF')
        self.text_rb = QLabel('RB')
        self.text_ikf = QLabel('IKF')
        self.text_ise = QLabel('ISE')
        self.text_ne = QLabel('NE')
        self.text_re = QLabel('RE')
        self.text_rc = QLabel('RC')

        self.test_button = QPushButton('Тест транзистора')
        self.test_button.clicked.connect(lambda: self.bjt_test())
        self.extraction_button = QPushButton('Экстракция SPICE-параметров')
        self.extraction_button.clicked.connect(lambda: self.bjt_extraction())
        self.stop_button = QPushButton('Стоп')
        self.stop_button.setStyleSheet('QPushButton {color: red;}')
        #self.stop_button.setFixedSize(100, 84)
        self.stop_button.clicked.connect(lambda: self.bjt_stop())

        self.connect_button = QPushButton('Подключиться к порту')
        self.connect_button.clicked.connect(lambda: self.connect_module())
        self.refresh_button = QPushButton("Обновить список портов")
        self.refresh_button.clicked.connect(lambda: self.refresh_ports())

        # -------------------------------------------------------
        top_layout.addWidget(self.field_results)
        top_layout.addWidget(self.field_control)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.field_model)
        self.field_results.setLayout(results_layout)
        self.field_control.setLayout(control_layout)
        self.field_model.setLayout(model_layout)
        results_layout.addWidget(self.text_type, 0, 0)
        results_layout.addWidget(self.text_pinout, 1, 0)
        results_layout.addWidget(self.text_is, 2, 0)
        results_layout.addWidget(self.text_bf, 3, 0)
        results_layout.addWidget(self.text_nf, 4, 0)
        results_layout.addWidget(self.text_rb, 5, 0)
        results_layout.addWidget(self.text_ikf, 6, 0)
        results_layout.addWidget(self.text_ise, 7, 0)
        results_layout.addWidget(self.text_ne, 8, 0)
        results_layout.addWidget(self.text_re, 9, 0)
        results_layout.addWidget(self.text_rc, 10, 0)
        results_layout.addWidget(self.input_type, 0, 1)
        results_layout.addWidget(self.input_pinout, 1, 1)
        results_layout.addWidget(self.input_is, 2, 1)
        results_layout.addWidget(self.input_bf, 3, 1)
        results_layout.addWidget(self.input_nf, 4, 1)
        results_layout.addWidget(self.input_rb, 5, 1)
        results_layout.addWidget(self.input_ikf, 6, 1)
        results_layout.addWidget(self.input_ise, 7, 1)
        results_layout.addWidget(self.input_ne, 8, 1)
        results_layout.addWidget(self.input_re, 9, 1)
        results_layout.addWidget(self.input_rc, 10, 1)
        control_layout.addWidget(self.text_connect)
        control_layout.addWidget(self.combo_ports)
        control_layout.addWidget(self.connect_button)
        control_layout.addWidget(self.refresh_button)
        control_layout.addWidget(self.input_logs)
        control_layout.addWidget(self.test_button)
        control_layout.addWidget(self.extraction_button)
        control_layout.addWidget(self.stop_button)
        model_layout.addWidget(self.input_model)

        container = QWidget()

        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Последовательный порт
        self.serial = QSerialPort(self)
        self.serial.setBaudRate(9600)
        self.serial.setDataBits(QSerialPort.DataBits.Data8)
        self.serial.setParity(QSerialPort.Parity.NoParity)
        self.serial.setStopBits(QSerialPort.StopBits.OneStop)
        self.serial.setFlowControl(
            QSerialPort.FlowControl.NoFlowControl
        )

        # Приём входящих данных
        self.rx_buffer = bytearray()
        self.serial.readyRead.connect(self.read_serial)
        self.serial.errorOccurred.connect(self.serial_error)

        # Результаты определения транзистора
        self.transistor_type = None
        self.transistor_pinout = None
        self.measurement_success = False

        # Массивы измерений
        self.gummel_data = []
        self.vbe_ib_data = []
        self.vce_ib_data = []

        # Состояние сложного измерения
        self.complex_measurement_active = False
        self.complex_measurement_complete = False

        self.refresh_ports()

    def log_message(self, message):
        """Вывод сообщения в журнал интерфейса."""
        self.input_logs.appendPlainText(
            message + "\n"
        )

    def refresh_ports(self):
        """Обновляет список доступных COM-портов."""
        current_port = self.combo_ports.currentData()

        self.combo_ports.clear()

        ports = QSerialPortInfo.availablePorts()

        for port in ports:
            self.combo_ports.addItem(
                f"{port.portName()} — {port.description()}",
                port.portName()
            )

        # По возможности сохраняем ранее выбранный порт
        index = self.combo_ports.findData(current_port)

        if index >= 0:
            self.combo_ports.setCurrentIndex(index)

        if self.combo_ports.count() == 0:
            self.combo_ports.addItem("Порты не найдены", None)
            self.log_message("Не найдено доступных COM-портов.")

    def read_serial(self):
        """Принимает данные из Serial и выделяет полные строки."""
        self.rx_buffer.extend(bytes(self.serial.readAll()))

        while b"\n" in self.rx_buffer:
            raw_line, _, remainder = self.rx_buffer.partition(b"\n")
            self.rx_buffer = bytearray(remainder)

            line = raw_line.decode(
                "utf-8", errors="replace"
            ).strip()

            if line:
                self.log_message(f"Arduino → ПК: {line}")
                self.process_message(line)

    def serial_error(self, error):
        """Обрабатывает ошибки последовательного порта."""
        if error == QSerialPort.SerialPortError.NoError:
            return

        self.log_message(
            f"Ошибка Serial: {self.serial.errorString()}"
        )

    def process_message(self, line):
        """Разбирает входящие сообщения от Arduino."""

        fields = [field.strip() for field in line.split(",")]

        try:
            code = fields[0]

            # -----------------------------------------
            # 001 — Arduino подтвердила подключение
            # -----------------------------------------
            if code == "001":
                if fields[1] == '1':
                    self.text_connect.setText(
                        f"Модуль: подключен (T-SPEX M1)"
                    )
                    self.log_message(
                        "Модуль инициализирован успешно (T-SPEX M1)."
                    )
                    return

            # -----------------------------------------
            # 000 — Arduino остановила измерение
            # -----------------------------------------
            if code == "000":
                self.complex_measurement_active = False
                self.complex_measurement_complete = False

                self.log_message(
                    "Arduino остановила процесс сложного измерения."
                )
                return

            # -----------------------------------------
            # 010 — простой тест транзистора
            # Формат: 010,success,type,pinout
            # -----------------------------------------
            if code == "010":
                success = int(fields[1])

                self.measurement_success = bool(success)

                if success:
                    transistor_type = int(fields[2])
                    pinout = fields[3]

                    self._validate_transistor(
                        transistor_type, pinout
                    )

                    self.transistor_type = (
                        "NPN" if transistor_type == 1 else "PNP"
                    )
                    self.transistor_pinout = pinout

                    self.input_type.setText(self.transistor_type)
                    self.input_pinout.setText(pinout)

                    self.log_message(
                        f"Простой тест завершён: "
                        f"{self.transistor_type}, "
                        f"распиновка {pinout}"
                    )
                else:
                    self.transistor_type = None
                    self.transistor_pinout = None

                    self.input_type.clear()
                    self.input_pinout.clear()

                    self.log_message(
                        "Простой тест завершён: "
                        "транзистор не определён"
                    )

                    QMessageBox.critical(
                        self,
                        "Ошибка измерения: промеряемый образец неисправен",
                        self.serial.errorString()
                    )

                return

            # -----------------------------------------
            # 020 — заголовок сложного теста
            # Формат: 020,success,type,pinout
            # -----------------------------------------
            if code == "020":
                success = int(fields[1])

                # Начинается новый набор измерений
                self.gummel_data.clear()
                self.vbe_ib_data.clear()
                self.vce_ib_data.clear()

                self.complex_measurement_complete = False
                self.complex_measurement_active = bool(success)
                self.measurement_success = bool(success)

                self.transistor_type = None
                self.transistor_pinout = None

                self.input_type.clear()
                self.input_pinout.clear()

                # Проверяем, определён ли транзистор
                if success:
                    transistor_type = int(fields[2])
                    pinout = fields[3]

                    self._validate_transistor(
                        transistor_type, pinout
                    )

                    self.transistor_type = (
                        "NPN" if transistor_type == 1 else "PNP"
                    )
                    self.transistor_pinout = pinout

                    self.input_type.setText(self.transistor_type)
                    self.input_pinout.setText(pinout)

                    self.log_message(
                        f"Начато сложное измерение: "
                        f"{self.transistor_type}, "
                        f"распиновка {pinout}"
                    )
                else:
                    self.log_message(
                        "Не удалось определить транзистор. "
                        "Сложное измерение не начато."
                    )

                    QMessageBox.critical(
                        self,
                        "Ошибка измерения: промеряемый образец неисправен",
                        self.serial.errorString()
                    )

                return

            # -----------------------------------------
            # 020 — завершение сложного теста
            # Формат: 020,2
            # -----------------------------------------
            if code == "020" and len(fields) == 2:
                status = int(fields[1])

                if status == 2:
                    if not self.complex_measurement_active:
                        self.log_message(
                            "Получен признак завершения, "
                            "но активного сложного теста нет."
                        )
                        return

                    self.complex_measurement_active = False
                    self.complex_measurement_complete = True

                    self.log_message(
                        "Сложное измерение успешно завершено.\n"
                        f"Точек Gummel: {len(self.gummel_data)}\n"
                        f"Точек Vbe(Ib): {len(self.vbe_ib_data)}\n"
                        f"Точек Vce(Ib): {len(self.vce_ib_data)}"
                    )
                elif status == 0:
                    self.complex_measurement_active = False
                    self.complex_measurement_complete = False

                    self.log_message(
                        "Сложное измерение завершено с ошибкой."
                    )
                else:
                    raise ValueError(
                        f"Неизвестный статус завершения: {status}"
                    )

                return

            # Точки измерений допустимы только
            # во время активного сложного теста
            if not self.complex_measurement_active:
                self.log_message(
                    f"Игнорируется сообщение {code}: "
                    "сложное измерение не активно."
                )
                return

            # -----------------------------------------
            # 021 — точки кривых Гуммеля
            # Формат: 021,Vbe,Ic,Ib
            # -----------------------------------------
            if code == "021":
                if len(fields) != 4:
                    raise ValueError(
                        "Для сообщения 021 требуется 4 поля"
                    )

                vbe, ic, ib = map(float, fields[1:4])

                self._validate_numbers(vbe, ic, ib)

                self.gummel_data.append([vbe, ic, ib])

                self.log_message(
                    f"Gummel: Vbe={vbe}, Ic={ic}, Ib={ib}"
                )
                return

            # -----------------------------------------
            # 022 — зависимость Vbe(Ib)
            # Формат: 022,Ib,Vbe
            # -----------------------------------------
            if code == "022":
                if len(fields) != 3:
                    raise ValueError(
                        "Для сообщения 022 требуется 3 поля"
                    )

                ib, vbe = map(float, fields[1:3])

                self._validate_numbers(ib, vbe)

                self.vbe_ib_data.append([ib, vbe])

                self.log_message(
                    f"Vbe(Ib): Ib={ib}, Vbe={vbe}"
                )
                return

            # -----------------------------------------
            # 023 — зависимость Vce(Ib)
            # Формат: 023,Ib,Vce
            # -----------------------------------------
            if code == "023":
                if len(fields) != 3:
                    raise ValueError(
                        "Для сообщения 023 требуется 3 поля"
                    )

                ib, vce = map(float, fields[1:3])

                self._validate_numbers(ib, vce)

                self.vce_ib_data.append([ib, vce])

                self.log_message(
                    f"Vce(Ib): Ib={ib}, Vce={vce}"
                )
                return

            self.log_message(
                f"Неизвестный код сообщения: {code}"
            )

        except (ValueError, IndexError) as error:
            self.log_message(
                f"Ошибка разбора строки '{line}': {error}"
            )

    def _validate_transistor(self, transistor_type, pinout):
        """Проверяет тип транзистора и формат распиновки."""

        if transistor_type not in (1, 2):
            raise ValueError(
                "Тип транзистора должен быть 1 (NPN) или 2 (PNP)"
            )

        if (
                len(pinout) != 3
                or not pinout.isdigit()
                or sorted(pinout) != ["1", "2", "3"]
        ):
            raise ValueError(
                "Распиновка должна быть перестановкой цифр 123"
            )

    def _validate_numbers(self, *values):
        """Отклоняет NaN и бесконечные значения."""
        import math

        if not all(math.isfinite(value) for value in values):
            raise ValueError(
                "Измерения содержат NaN или бесконечность"
            )

    def send_command(self, command):
        """Отправляет команду Arduino в формате ASCII + LF."""

        if not self.serial.isOpen():
            self.log_message(
                f"Команда {command} не отправлена: модуль не подключён."
            )
            return False

        command = str(command).strip()

        if not command.isdigit() or len(command) != 3:
            self.log_message(f"Некорректная команда: {command}")
            return False

        payload = (command + "\n").encode("ascii")
        written = self.serial.write(payload)

        if written != len(payload):
            self.log_message(
                f"Не удалось полностью отправить команду {command}."
            )
            return False

        self.serial.flush()
        self.log_message(f"ПК → Arduino: {command}")
        return True

    def connect_module(self):
        """Открывает или закрывает выбранный Serial-порт."""

        if self.serial.isOpen():
            self.serial.close()
            self.text_connect.setText("Модуль: не подключен")
            self.connect_button.setText(
                "Подключиться к порту"
            )
            self.log_message("Соединение закрыто.")
            return

        port_name = self.combo_ports.currentData()

        if not port_name:
            QMessageBox.warning(
                self,
                "Ошибка подключения",
                "Выберите доступный COM-порт."
            )
            return

        self.serial.setPortName(port_name)

        if self.serial.open(QIODevice.OpenModeFlag.ReadWrite):
            self.rx_buffer.clear()
            self.send_command("101")
            self.log_message(
                f"Соединение установлено: {port_name}"
            )
            self.connect_button.setText("Отключиться от порта")
            self.log_message(
                f"Ожидание подтвеждения подключения модуля..."
            )
            self.send_command("101")
        else:
            QMessageBox.critical(
                self,
                "Ошибка подключения",
                self.serial.errorString()
            )

    def bjt_test(self):
        """Запуск простого измерения."""
        self.send_command("110")

    def bjt_extraction(self):
        """Запуск сложного измерения."""

        if not self.serial.isOpen():
            self.log_message(
                "Нельзя начать измерение: модуль не подключён."
            )
            return

        # Сбрасываем результаты предыдущего измерения.
        self.gummel_data.clear()
        self.vbe_ib_data.clear()
        self.vce_ib_data.clear()

        # Ожидаем подтверждение начала от Arduino
        # в сообщении 020,success,type,pinout.
        self.complex_measurement_active = False
        self.complex_measurement_complete = False

        self.send_command("120")

    def bjt_stop(self):
        """Остановка сложного измерения."""

        if not self.serial.isOpen():
            self.log_message(
                "Нельзя остановить измерение: модуль не подключён."
            )
            return

        if not self.complex_measurement_active:
            self.log_message(
                "Сложное измерение сейчас не активно."
            )
            return

        if self.send_command("100"):
            # Немедленно запрещаем GUI принимать новые точки.
            self.complex_measurement_active = False
            self.complex_measurement_complete = False

            self.log_message(
                "Запрошена остановка сложного измерения."
            )



if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())