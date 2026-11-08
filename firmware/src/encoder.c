#include "encoder.h"
#include "board.h"

/* ============================================================
 * ENCODER.H – API CHO 4 ENCODER JGB37-520
 * - Encoder 1–3: TIM2/3/4 encoder mode (phần cứng)
 * - Encoder 4:   EXTI8 + software quadrature decode
 * ============================================================ */

/* Khai báo extern các timer handle từ main.c */
extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim3;
extern TIM_HandleTypeDef htim4;

/* Bảng chuyển trạng thái quadrature x4 */
static const int8_t quadrature_table[16] = {
     0, -1,  1,  0,
     1,  0,  0, -1,
    -1,  0,  0,  1,
     0,  1, -1,  0
};

/* Đọc trạng thái chân A và B của encoder:
 * - a = 1 nếu HIGH, ngược lại 0
 * - b = 1 nếu HIGH, ngược lại 0
 * Trả về (a<<1)|b */
///* Đọc trạng thái chân A/B của encoder và mã hóa thành giá trị 2-bit:
 * a = bit 1, b = bit 0 => state = (a << 1) | b */
static uint8_t read_state(Encoder *enc)
{
    uint8_t a = (HAL_GPIO_ReadPin(enc->port_a, enc->pin_a) == GPIO_PIN_SET) ? 1u : 0u;
    uint8_t b = (HAL_GPIO_ReadPin(enc->port_b, enc->pin_b) == GPIO_PIN_SET) ? 1u : 0u;
    return (uint8_t)((a << 1) | b);
}

/* Khởi tạo encoder:
 * - id: mã encoder (1..4)
 * - timer: con trỏ TIM (NULL cho encoder phần mềm M4)
 * - port/pin_a, port/pin_b: chân A/B của encoder
 * - invert: đảo chiều đếm (0 = bình thường, 1 = đảo)
 * Nếu timer != NULL, bật TIM encoder mode và reset counter. */
void encoder_init(Encoder *enc, EncoderId id,
                  TIM_HandleTypeDef *timer,
                  GPIO_TypeDef *port_a, uint16_t pin_a,
                  GPIO_TypeDef *port_b, uint16_t pin_b,
                  uint8_t invert)
{
    enc->id          = id;
    enc->timer       = timer;
    enc->port_a      = port_a;
    enc->pin_a       = pin_a;
    enc->port_b      = port_b;
    enc->pin_b       = pin_b;
    enc->invert      = invert;
    enc->sw_count    = 0;
    enc->last_count  = 0;
    enc->prev_state  = read_state(enc);

    if (timer != NULL) {
        HAL_TIM_Encoder_Start(timer, TIM_CHANNEL_ALL);
        __HAL_TIM_SET_COUNTER(timer, 0);
    }
}

/* Lấy delta (số xung thay đổi) của encoder:
 * - Timer phần cứng: đọc __HAL_TIM_GET_COUNTER và xử lý tràn 16-bit.
 * - Encoder phần mềm M4: đọc enc->sw_count (không reset ở đây để tránh lỗi RPM).
 * Trả về delta đã áp dụng invert nếu cần. */
int32_t encoder_take_delta(Encoder *enc)
{
    int32_t current_count = 0;
    int32_t delta;

    if (enc->timer != NULL) {
        current_count = (int32_t)__HAL_TIM_GET_COUNTER(enc->timer);
    } else {
        uint32_t primask = __get_PRIMASK();
        __disable_irq();
        current_count = enc->sw_count;
        if (primask == 0u) {
            __enable_irq();
        }
    }

    delta = current_count - enc->last_count;

    if (enc->timer != NULL) {
        if (delta > 32767)  delta -= 65536;
        if (delta < -32768) delta += 65536;
    }

    enc->last_count = current_count;

    return enc->invert ? -delta : delta;
}

/* Tính RPM từ delta xung:
 * RPM = (delta / CPR / dt_sec) * 60
 * cpr = số xung mỗi vòng, dt_sec = thời gian giữa 2 lần đọc (s). */
float encoder_get_rpm(Encoder *enc, int32_t delta, float cpr, float dt_sec)
{
    (void)enc;
    if (dt_sec <= 0.0f || cpr <= 0.0f) {
        return 0.0f;
    }
    return ((float)delta / cpr / dt_sec) * 60.0f;
}

/* Xử lý cạnh encoder cho encoder phần mềm (M4):
 * - Nếu timer != NULL: bỏ qua (encoder phần cứng xử lý).
 * - Nếu timer == NULL: đọc trạng thái A/B, dùng bảng quadrature để tính delta
 *   và cộng vào enc->sw_count. */
void encoder_handle_edge(Encoder *enc)
{
    uint8_t state;
    uint8_t index;
    int8_t delta;

    if (enc->timer != NULL) {
        return;
    }

    state = read_state(enc);
    index = (uint8_t)((enc->prev_state << 2) | state);
    delta = quadrature_table[index & 0x0Fu];

    enc->sw_count += delta;
    enc->prev_state = state;
}

/* Reset encoder:
 * - Timer phần cứng: reset counter về 0.
 * - Encoder phần mềm: reset sw_count về 0.
 * - last_count về 0 (để lần đọc tiếp theo tính delta đúng). */
void encoder_reset(Encoder *enc)
{
    if (enc->timer != NULL) {
        __HAL_TIM_SET_COUNTER(enc->timer, 0);
    } else {
        uint32_t primask = __get_PRIMASK();
        __disable_irq();
        enc->sw_count = 0;
        if (primask == 0u) {
            __enable_irq();
        }
    }
    enc->last_count = 0;
}