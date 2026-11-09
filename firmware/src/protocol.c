#include "protocol.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "control.h"
#include "robot_config.h"
#include "stm32f1xx_hal.h"

extern UART_HandleTypeDef huart2;

static volatile uint8_t rx_ring[RX_RING_SIZE];
static volatile uint16_t rx_head;
static volatile uint16_t rx_tail;

static char line_buffer[PROTOCOL_LINE_MAX];
static uint16_t line_length;
static uint8_t line_overflow;

static char tx_buffer[TX_BUFFER_SIZE];

static uint32_t last_rx_ms;
static uint8_t has_rx;

static void mark_alive(void)
{
    last_rx_ms = HAL_GetTick();
    has_rx = 1u;
}

/* Parser số thực từ chuỗi text:
 * - text: chuỗi đầu vào
 * - values: mảng chứa kết quả
 * - max_values: số lượng tối đa
 * Trả về số lượng số thực đã parse, -1 nếu lỗi */
static int parse_floats(const char *text, float *values, int max_values)
{
    const char *cursor = text;
    int count = 0;

    while (count < max_values) {
        char *end = NULL;
        float value = strtof(cursor, &end);
        if (end == cursor) {
            break;
        }
        values[count++] = value;
        cursor = end;
        while (*cursor == ' ' || *cursor == '\t') {
            cursor++;
        }
        if (*cursor == ',') {
            cursor++;
            continue;
        }
        break;
    }

    while (*cursor == ' ' || *cursor == '\t') {
        cursor++;
    }
    if (*cursor != '\0' && *cursor != '\r') {
        return -1;
    }
    return count;
}

/* Kiểm tra giá trị hợp lệ:
 * - Không NaN
 * - Trong khoảng [-1e6, 1e6]
 * Trả về 1 nếu hợp lệ, 0 nếu không */
static int values_are_sane(const float *values, int count)
{
    int index;
    for (index = 0; index < count; index++) {
        float value = values[index];
        if (value != value || value > 1000000.0f || value < -1000000.0f) {
            return 0;
        }
    }
    return 1;
}

/* Gửi text qua UART:
 * - Poll cờ TXE rồi ghi DR trực tiếp (không dùng HAL_UART_Transmit_IT).
 *   Cách này tránh kẹt cờ tx_busy khi callback TX complete bị lỡ
 *   (RX đọc DR đồng thời với ISR TX có thể làm HAL state machine treo).
 * - Timeout 10 ms mỗi byte; hết thời gian thì thoát im lặng. */
static void send_text(const char *text)
{
    size_t length = strlen(text);
    size_t i;
    uint32_t start;

    if (length == 0u || length >= TX_BUFFER_SIZE) {
        return;
    }
    memcpy(tx_buffer, text, length);

    for (i = 0u; i < length; i++) {
        start = HAL_GetTick();
        while (!__HAL_UART_GET_FLAG(&huart2, UART_FLAG_TXE)) {
            if ((uint32_t)(HAL_GetTick() - start) > 10u) {
                return;
            }
        }
        huart2.Instance->DR = (uint8_t)tx_buffer[i];
    }
}

/* Xử lý một dòng lệnh từ host:
 * - STOP: dừng motor
 * - PING: trả PONG
 * - P: chỉnh PID
 * - D: chỉnh dead-zone
 * - M: PWM thủ công
 * - V: lệnh vận tốc
 * - R: lệnh RPM trực tiếp
 * - Nếu không có tiền tố: parse số và tự động phân loại */
static void handle_line(char *line)
{
    float values[5];
    int count;

    if (strncmp(line, "STOP", 4) == 0 && line[4] == '\0') {
        control_stop();
        mark_alive();
        return;
    }

    if (strncmp(line, "PING", 4) == 0 && line[4] == '\0') {
        send_text("PONG\n");
        mark_alive();
        return;
    }

    if ((line[0] == 'P' || line[0] == 'p') && line[1] == ',') {
        count = parse_floats(line + 2, values, 4);
        if (count == 4 && values_are_sane(values, 4)) {
            int index = (int)values[0];
            if (index >= 1 && index <= 4) {
                control_set_pid((uint8_t)(index - 1), values[1], values[2], values[3]);
                mark_alive();
            }
        }
        return;
    }

    if ((line[0] == 'D' || line[0] == 'd') && line[1] == ',') {
        count = parse_floats(line + 2, values, 2);
        if (count == 2 && values_are_sane(values, 2)) {
            int index = (int)values[0];
            if (index >= 1 && index <= 4) {
                control_set_deadzone((uint8_t)(index - 1), values[1]);
                mark_alive();
            }
        }
        return;
    }

    if ((line[0] == 'M' || line[0] == 'm') && line[1] == ',') {
        count = parse_floats(line + 2, values, 2);
        if (count == 2 && values_are_sane(values, 2)) {
            int index = (int)values[0];
            if (index >= 1 && index <= 4) {
                control_set_manual((uint8_t)(index - 1), values[1]);
                mark_alive();
            }
        }
        return;
    }

    if ((line[0] == 'V' || line[0] == 'v') && line[1] == ',') {
        count = parse_floats(line + 2, values, 3);
        if (count == 3 && values_are_sane(values, 3)) {
            control_set_velocity(values[0], values[1], values[2]);
            mark_alive();
        }
        return;
    }

    if ((line[0] == 'R' || line[0] == 'r') && line[1] == ',') {
        count = parse_floats(line + 2, values, 4);
        if (count == 4 && values_are_sane(values, 4)) {
            control_set_wheel_rpm(values);
            mark_alive();
        }
        return;
    }

    count = parse_floats(line, values, 5);
    if (count == 3 && values_are_sane(values, 3)) {
        control_set_velocity(values[0], values[1], values[2]);
        mark_alive();
    } else if (count == 4 && values_are_sane(values, 4)) {
        control_set_wheel_rpm(values);
        mark_alive();
    }
}

/* Khởi tạo protocol:
 * - Reset ring buffer
 * - Reset line buffer
 * - Đặt last_rx_ms = HAL_GetTick() */
void protocol_init(void)
{
    rx_head = 0u;
    rx_tail = 0u;
    line_length = 0u;
    line_overflow = 0u;
    last_rx_ms = HAL_GetTick();
    has_rx = 0u;
}

/* Nhận byte từ UART ISR:
 * - Đưa byte vào ring buffer
 * - Nếu ring buffer đầy: bỏ qua (không blocking) */
void protocol_rx_byte(uint8_t byte)
{
    uint16_t next = (uint16_t)((rx_head + 1u) % RX_RING_SIZE);
    if (next != rx_tail) {
        rx_ring[rx_head] = byte;
        rx_head = next;
    }
}

/* Xử lý ring buffer:
 * - Lấy byte từ ring buffer
 * - Nếu '\n': parse line và xử lý
 * - Nếu '\r': bỏ qua
 * - Nếu khác: thêm vào line_buffer */
void protocol_process(void)
{
    while (rx_tail != rx_head) {
        char character = (char)rx_ring[rx_tail];
        rx_tail = (uint16_t)((rx_tail + 1u) % RX_RING_SIZE);

        if (character == '\r') {
            continue;
        }

        if (character == '\n') {
            if (!line_overflow && line_length > 0u) {
                line_buffer[line_length] = '\0';
                handle_line(line_buffer);
            }
            line_length = 0u;
            line_overflow = 0u;
            continue;
        }

        if (line_length < PROTOCOL_LINE_MAX - 1u) {
            line_buffer[line_length++] = character;
        } else {
            line_overflow = 1u;
        }
    }
}

/* Kiểm tra host còn sống:
 * - Nếu chưa nhận byte nào: false
 * - Nếu quá timeout (500 ms): false
 * - Ngược lại: true */
uint8_t protocol_is_alive(uint32_t now_ms)
{
    if (!has_rx) {
        return 0u;
    }
    return (uint32_t)(now_ms - last_rx_ms) <= ROBOT_UART_TIMEOUT_MS ? 1u : 0u;
}

uint32_t protocol_last_rx_ms(void)
{
    return last_rx_ms;
}

static long rpm_x10(float rpm)
{
    if (rpm >= 0.0f) {
        return (long)(rpm * 10.0f + 0.5f);
    }
    return (long)(rpm * 10.0f - 0.5f);
}

/* Gửi telemetry về host:
 * - Format: T,<t_ms>,<rpm_act x4>,<rpm_set x4>
 * - RPM nhân 10 để tránh printf float
 * - KHÔNG dùng HAL_UART_Transmit_IT: poll TXE rồi ghi DR để tránh kẹt tx_busy */
void protocol_send_telemetry(uint32_t now_ms)
{
    float actual[4];
    float target[4];
    int length;
    size_t i;
    uint32_t start;

    control_get_actual_rpm(actual);
    control_get_target_rpm(target);

    length = snprintf(tx_buffer, TX_BUFFER_SIZE,
                      "T,%lu,%ld,%ld,%ld,%ld,%ld,%ld,%ld,%ld\n",
                      (unsigned long)now_ms,
                      rpm_x10(actual[0]), rpm_x10(actual[1]), rpm_x10(actual[2]), rpm_x10(actual[3]),
                      rpm_x10(target[0]), rpm_x10(target[1]), rpm_x10(target[2]), rpm_x10(target[3]));
    if (length <= 0 || length >= (int)TX_BUFFER_SIZE) {
        return;
    }

    for (i = 0; i < (size_t)length; i++) {
        start = HAL_GetTick();
        while (!__HAL_UART_GET_FLAG(&huart2, UART_FLAG_TXE)) {
            if ((uint32_t)(HAL_GetTick() - start) > 10u) {
                return;
            }
        }
        huart2.Instance->DR = (uint8_t)tx_buffer[i];
    }
}

/* Không còn dùng ngắt TX complete; giữ hàm để tương thích với callback hiện hành. */
void protocol_tx_complete(void)
{
}
