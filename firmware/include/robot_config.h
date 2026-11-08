#ifndef ROBOT_CONFIG_H
#define ROBOT_CONFIG_H

/* ============================================================
 * ROBOT_CONFIG.H – THÔNG SỐ CẤU HÌNH ROBOT MECANUM 4 BÁNH
 * Cập nhật: Pinout mới (3 timer + 1 EXTI, 4 PWM + 4 DIR)
 * ============================================================ */

/* ------------------------------------------------------------
 * 1. CHU KỲ ĐIỀU KHIỂN & TRUYỀN THÔNG
 * ------------------------------------------------------------ */
#define ROBOT_CONTROL_PERIOD_MS     10u    /* 100 Hz – PID */
#define ROBOT_TELEMETRY_PERIOD_MS   20u    /* 50 Hz – telemetry */
#define ROBOT_UART_TIMEOUT_MS       500u   /* mất lệnh → dừng */

/* ------------------------------------------------------------
 * 2. HÌNH HỌC ROBOT (đo thực tế trước khi chạy PID)
 * ------------------------------------------------------------ */
#define WHEEL_RADIUS_M      0.04f    /* bánh Mecanum Ø80 mm */
#define WHEELBASE_M         0.25f    /* khoảng cách tâm bánh trước–sau */
#define TRACK_WIDTH_M       0.20f    /* khoảng cách tâm bánh trái–phải */
#define YAW_ARM_M           ((WHEELBASE_M + TRACK_WIDTH_M) * 0.5f)

/* ------------------------------------------------------------
 * 3. ENCODER
 * ------------------------------------------------------------ */
#define ENCODER_CPR         1320.0f  /* counts/vòng trục ra (11×30×4) */
#define MAX_WHEEL_RPM       333.0f   /* JGB37-520 12V */
#define ENC4_SW_QUADRATURE  1u       /* 1 = encoder 4 dùng software x4 */

/* Đảo chiều nếu cần (sau khi test thực tế) */
#define VY_INVERTED         0
#define OMEGA_INVERTED      0

/* ------------------------------------------------------------
 * 4. PWM
 * ------------------------------------------------------------ */
#define PWM_TIM_ARR         3599u    /* 72 MHz / 20 kHz - 1 */
#define PWM_FREQUENCY_HZ    20000u
#define PWM_MAX_DUTY        1.0f     /* 1.0 = 100%, 0.7 = 70% nếu cần giới hạn */

/* ------------------------------------------------------------
 * 5. PID
 * ------------------------------------------------------------ */
#define PID_KP_DEFAULT      0.0035f
#define PID_KI_DEFAULT      0.015f
#define PID_KD_DEFAULT      0.00015f
#define PID_OUT_MIN         (-1.0f)
#define PID_OUT_MAX         (1.0f)
#define PID_I_MIN           (-0.5f)
#define PID_I_MAX           (0.5f)
#define PID_D_FILTER_ALPHA  0.30f
#define DEADZONE_DEFAULT    0.08f

/* ------------------------------------------------------------
 * 6. BẢO VỆ & AN TOÀN
 * ------------------------------------------------------------ */
#define MOTOR_CURRENT_LIMIT_A   5.0f    /* dòng kẹp JGB37-520 */
#define ESTOP_DEBOUNCE_MS       20u     /* chống dội nút E-stop */

/* ------------------------------------------------------------
 * 7. UART & PROTOCOL
 * ------------------------------------------------------------ */
#define UART_BAUDRATE       115200u
#define PROTOCOL_LINE_MAX   96u
#define RX_RING_SIZE        256u
#define TX_BUFFER_SIZE      128u

#endif /* ROBOT_CONFIG_H */