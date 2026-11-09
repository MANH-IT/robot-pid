#ifndef ROBOT_CONFIG_H
#define ROBOT_CONFIG_H

/* ============================================================
 * ROBOT_CONFIG.H – THÔNG SỐ CẤU HÌNH ROBOT MECANUM 4 BÁNH
 * Cập nhật: Pinout mới (2 timer + 2 EXTI, 8 PWM RPWM/LPWM BTS7960)
 * ============================================================ */

/* Chu kỳ điều khiển & truyền thông:
 * - 10 ms (100 Hz) cho PID
 * - 20 ms (50 Hz) cho telemetry
 * - 500 ms timeout mất lệnh */
#define ROBOT_CONTROL_PERIOD_MS     10u    /* 100 Hz – PID */
#define ROBOT_TELEMETRY_PERIOD_MS   20u    /* 50 Hz – telemetry */
#define ROBOT_UART_TIMEOUT_MS       500u   /* mất lệnh → dừng */

/* Hình học robot (đo thực tế trước khi chạy PID):
 * - R = 0.04 m (bánh Ø80 mm)
 * - k = (wheelbase + track) / 2
 * - YAW_ARM_M = k */
#define WHEEL_RADIUS_M      0.04f    /* bánh Mecanum Ø80 mm */
#define WHEELBASE_M         0.25f    /* khoảng cách tâm bánh trước–sau */
#define TRACK_WIDTH_M       0.20f    /* khoảng cách tâm bánh trái–phải */
#define YAW_ARM_M           ((WHEELBASE_M + TRACK_WIDTH_M) * 0.5f)

/* Encoder:
 * - ENCODER_CPR = 1320 (11 PPR × 30 × 4) cho bánh 1 & 3 (encoder phần cứng TIM2/TIM4)
 * - ENCODER4_CPR = 660 (x2) cho bánh 2 & 4 vì chỉ ngắt cạnh A (giải mã mềm)
 *   (RPM báo đúng, nhưng độ phân giải chỉ bằng một nửa)
 * - MAX_WHEEL_RPM = 333 (JGB37-520 12V) */
#define ENCODER_CPR         1320.0f  /* counts/vòng trục ra, bánh 1 & 3 (x4) */
#define ENCODER4_CPR        660.0f   /* counts/vòng trục ra, bánh 2 & 4 (x2) */
#define MAX_WHEEL_RPM       333.0f   /* JGB37-520 12V */

/* Đảo chiều nếu cần (sau khi test thực tế) */
#define VY_INVERTED         0
#define OMEGA_INVERTED      0

/* PWM:
 * - ARR = 3599, prescaler = 0 → 72 MHz / 3600 = 20 kHz */
#define PWM_TIM_ARR         3199u    /* 64 MHz (HSI) / 20 kHz - 1 */
#define PWM_FREQUENCY_HZ    20000u

/* PID:
 * - Kp, Ki, Kd: hệ số P/I/D mặc định
 * - I term kẹp trong [-0.5, 0.5]
 * - D filter alpha = 0.30
 * - Dead-zone mặc định = 0.08 */
#define PID_KP_DEFAULT      0.0035f
#define PID_KI_DEFAULT      0.015f
#define PID_KD_DEFAULT      0.00015f
#define PID_OUT_MIN         (-1.0f)
#define PID_OUT_MAX         (1.0f)
#define PID_I_MIN           (-0.5f)
#define PID_I_MAX           (0.5f)
#define PID_D_FILTER_ALPHA  0.30f
#define DEADZONE_DEFAULT    0.08f

/* An toàn:
 * - E-STOP trên PC0 (EXTI0, cạnh xuống, pull-up).
 *   - Ở boot: main.c kiểm tra mức pin; nếu LOW → chốt emergency_flag.
 *   - Cờ emergency_flag chỉ xóa khi khởi động lại firmware. */

/* UART & Protocol:
 * - Baudrate 115200
 * - Line max 96 ký tự
 * - Ring buffer 256 byte
 * - TX buffer 128 byte */
#define UART_BAUDRATE       115200u
#define PROTOCOL_LINE_MAX   96u
#define RX_RING_SIZE        256u
#define TX_BUFFER_SIZE      128u

#endif /* ROBOT_CONFIG_H */