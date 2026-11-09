#include "stm32f1xx_hal.h"

#include "board.h"
#include "control.h"
#include "encoder.h"
#include "motor.h"
#include "protocol.h"
#include "robot_config.h"

UART_HandleTypeDef huart2;
TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim2;
TIM_HandleTypeDef htim3;
TIM_HandleTypeDef htim4;
IWDG_HandleTypeDef hiwdg;

static uint8_t rx_byte;

static void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_EXTI_NVIC_Init(void);
static void MX_TIM1_PWM_Init(void);
static void MX_TIM2_Encoder_Init(void);
static void MX_TIM3_PWM_Init(void);
static void MX_TIM4_Encoder_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_IWDG_Init(void);
static void Error_Handler(void);

int main(void)
{
    uint32_t last_control;
    uint32_t last_telemetry = 0u;
    uint32_t last_led = 0u;
    uint8_t led_on = 0u;

    HAL_Init();
    SystemClock_Config();

    MX_GPIO_Init();
    MX_TIM1_PWM_Init();
    MX_TIM2_Encoder_Init();
    MX_TIM3_PWM_Init();
    MX_TIM4_Encoder_Init();
    MX_USART2_UART_Init();

    /* Khởi tạo xong state trước, rồi mới bật ngắt EXTI:
     * tránh ISR chạy khi htim/protocol/control chưa sẵn sàng. */
    control_init();
    protocol_init();
    MX_EXTI_NVIC_Init();
    /* Sau khi NVIC đã bật: poll bắt nút E-STOP đang giữ (LOW) từ boot;
     * cạnh xuống sau thời điểm này do ISR bắt. Chốt dừng nếu cần. */
    if (HAL_GPIO_ReadPin(ESTOP_PORT, ESTOP_PIN) == GPIO_PIN_RESET) {
        control_emergency_stop();
    }
    MX_IWDG_Init();

    HAL_UART_Receive_IT(&huart2, &rx_byte, 1u);

    last_control = HAL_GetTick();

    while (1) {
        uint32_t now;
        protocol_process();
        HAL_IWDG_Refresh(&hiwdg);
        now = HAL_GetTick();

        if ((uint32_t)(now - last_control) >= ROBOT_CONTROL_PERIOD_MS) {
            float dt = (float)(now - last_control) / 1000.0f;
            uint8_t enabled;
            last_control = now;
            if (dt <= 0.0f) dt = 0.001f;
            enabled = protocol_is_alive(now);
            control_step(dt, enabled);
        }

        if ((uint32_t)(now - last_telemetry) >= ROBOT_TELEMETRY_PERIOD_MS) {
            last_telemetry = now;
            protocol_send_telemetry(now);
        }

        if ((uint32_t)(now - last_led) >= 500u) {
            last_led = now;
            led_on = led_on ? 0u : 1u;
            HAL_GPIO_WritePin(LED_PORT, LED_PIN, led_on ? GPIO_PIN_RESET : GPIO_PIN_SET);
        }
    }
}

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clocks = {0};

    /* Dùng HSI nội 64 MHz (HSI/2 x16) để tránh phụ thuộc thạch anh ngoài
     * (nhiều board Blue Pill clone có thạch anh sai tần số/không chạy),
     * đảm bảo baudrate USART2 = 115200 đúng và clock ổn định.
     * PWM_TIM_ARR = 3199 -> 64 MHz / 3200 = 20 kHz. */
    osc.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    osc.HSIState = RCC_HSI_ON;
    osc.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSI_DIV2;
    osc.PLL.PLLMUL = RCC_PLL_MUL16;

    if (HAL_RCC_OscConfig(&osc) != HAL_OK) {
        Error_Handler();
    }

    clocks.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                       RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clocks.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clocks.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clocks.APB1CLKDivider = RCC_HCLK_DIV2;
    clocks.APB2CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&clocks, FLASH_LATENCY_2) != HAL_OK) Error_Handler();
}

static void MX_TIM1_PWM_Init(void)
{
    TIM_ClockConfigTypeDef clock_source = {0};
    TIM_MasterConfigTypeDef master = {0};
    TIM_OC_InitTypeDef channel = {0};

    htim1.Instance = TIM1;
    htim1.Init.Prescaler = 0u;
    htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim1.Init.Period = PWM_TIM_ARR;
    htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim1.Init.RepetitionCounter = 0u;
    htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    if (HAL_TIM_PWM_Init(&htim1) != HAL_OK) Error_Handler();

    clock_source.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
    if (HAL_TIM_ConfigClockSource(&htim1, &clock_source) != HAL_OK) Error_Handler();

    master.MasterOutputTrigger = TIM_TRGO_RESET;
    master.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
    if (HAL_TIMEx_MasterConfigSynchronization(&htim1, &master) != HAL_OK) Error_Handler();

    channel.OCMode = TIM_OCMODE_PWM1;
    channel.Pulse = 0u;
    channel.OCPolarity = TIM_OCPOLARITY_HIGH;
    channel.OCNPolarity = TIM_OCNPOLARITY_HIGH;
    channel.OCFastMode = TIM_OCFAST_DISABLE;
    channel.OCIdleState = TIM_OCIDLESTATE_RESET;
    channel.OCNIdleState = TIM_OCNIDLESTATE_RESET;

    if (HAL_TIM_PWM_ConfigChannel(&htim1, &channel, TIM_CHANNEL_1) != HAL_OK) Error_Handler();
    if (HAL_TIM_PWM_ConfigChannel(&htim1, &channel, TIM_CHANNEL_2) != HAL_OK) Error_Handler();
    if (HAL_TIM_PWM_ConfigChannel(&htim1, &channel, TIM_CHANNEL_3) != HAL_OK) Error_Handler();
    if (HAL_TIM_PWM_ConfigChannel(&htim1, &channel, TIM_CHANNEL_4) != HAL_OK) Error_Handler();
}

static void MX_TIM_Encoder_Common(TIM_HandleTypeDef *htim, TIM_TypeDef *instance)
{
    TIM_Encoder_InitTypeDef sConfig = {0};
    TIM_MasterConfigTypeDef sMasterConfig = {0};

    htim->Instance = instance;
    htim->Init.Prescaler = 0;
    htim->Init.CounterMode = TIM_COUNTERMODE_UP;
    htim->Init.Period = 65535;
    htim->Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim->Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;

    sConfig.EncoderMode = TIM_ENCODERMODE_TI12;
    sConfig.IC1Polarity = TIM_ICPOLARITY_RISING;
    sConfig.IC1Selection = TIM_ICSELECTION_DIRECTTI;
    sConfig.IC1Prescaler = TIM_ICPSC_DIV1;
    sConfig.IC1Filter = 6;
    sConfig.IC2Polarity = TIM_ICPOLARITY_RISING;
    sConfig.IC2Selection = TIM_ICSELECTION_DIRECTTI;
    sConfig.IC2Prescaler = TIM_ICPSC_DIV1;
    sConfig.IC2Filter = 6;
    if (HAL_TIM_Encoder_Init(htim, &sConfig) != HAL_OK) Error_Handler();

    sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
    sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
    HAL_TIMEx_MasterConfigSynchronization(htim, &sMasterConfig);
}

static void MX_TIM2_Encoder_Init(void) { MX_TIM_Encoder_Common(&htim2, TIM2); }
static void MX_TIM3_PWM_Init(void)
{
    TIM_ClockConfigTypeDef clock_source = {0};
    TIM_MasterConfigTypeDef master = {0};
    TIM_OC_InitTypeDef channel = {0};

    htim3.Instance = TIM3;
    htim3.Init.Prescaler = 0u;
    htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim3.Init.Period = PWM_TIM_ARR;
    htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim3.Init.RepetitionCounter = 0u;
    htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    if (HAL_TIM_PWM_Init(&htim3) != HAL_OK) Error_Handler();

    clock_source.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
    if (HAL_TIM_ConfigClockSource(&htim3, &clock_source) != HAL_OK) Error_Handler();

    master.MasterOutputTrigger = TIM_TRGO_RESET;
    master.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
    if (HAL_TIMEx_MasterConfigSynchronization(&htim3, &master) != HAL_OK) Error_Handler();

    channel.OCMode = TIM_OCMODE_PWM1;
    channel.Pulse = 0u;
    channel.OCPolarity = TIM_OCPOLARITY_HIGH;
    channel.OCNPolarity = TIM_OCNPOLARITY_HIGH;
    channel.OCFastMode = TIM_OCFAST_DISABLE;
    channel.OCIdleState = TIM_OCIDLESTATE_RESET;
    channel.OCNIdleState = TIM_OCNIDLESTATE_RESET;

    if (HAL_TIM_PWM_ConfigChannel(&htim3, &channel, TIM_CHANNEL_1) != HAL_OK) Error_Handler();
    if (HAL_TIM_PWM_ConfigChannel(&htim3, &channel, TIM_CHANNEL_2) != HAL_OK) Error_Handler();
    if (HAL_TIM_PWM_ConfigChannel(&htim3, &channel, TIM_CHANNEL_3) != HAL_OK) Error_Handler();
    if (HAL_TIM_PWM_ConfigChannel(&htim3, &channel, TIM_CHANNEL_4) != HAL_OK) Error_Handler();
}
static void MX_TIM4_Encoder_Init(void) { MX_TIM_Encoder_Common(&htim4, TIM4); }

static void MX_USART2_UART_Init(void)
{
    huart2.Instance = USART2;
    huart2.Init.BaudRate = UART_BAUDRATE;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    if (HAL_UART_Init(&huart2) != HAL_OK) Error_Handler();
}

static void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef init = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    /* LED PC13 */
    HAL_GPIO_WritePin(LED_PORT, LED_PIN, GPIO_PIN_SET);
    init.Pin = LED_PIN;
    init.Mode = GPIO_MODE_OUTPUT_PP;
    init.Pull = GPIO_NOPULL;
    init.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(LED_PORT, &init);

    /* ENC2 A (PB10) – EXTI10 */
    init.Pin = ENC2_A_PIN;
    init.Mode = GPIO_MODE_IT_RISING_FALLING;
    init.Pull = GPIO_PULLUP;
    init.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(ENC2_A_PORT, &init);

    /* ENC2 B (PB11) – GPIO in */
    init.Pin = ENC2_B_PIN;
    init.Mode = GPIO_MODE_INPUT;
    init.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(ENC2_B_PORT, &init);

    /* ENC4 A (PB8) – EXTI8 */
    init.Pin = ENC4_A_PIN;
    init.Mode = GPIO_MODE_IT_RISING_FALLING;
    init.Pull = GPIO_PULLUP;
    init.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(ENC4_A_PORT, &init);

    /* ENC4 B (PB9) – GPIO in */
    init.Pin = ENC4_B_PIN;
    init.Mode = GPIO_MODE_INPUT;
    init.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(ENC4_B_PORT, &init);

    /* E-stop PC0 – EXTI0 */
    init.Pin = ESTOP_PIN;
    init.Mode = GPIO_MODE_IT_FALLING;
    init.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(ESTOP_PORT, &init);

    /* NVIC cho EXTI bật sau trong MX_EXTI_NVIC_Init() */
}

static void MX_EXTI_NVIC_Init(void)
{
    HAL_NVIC_SetPriority(EXTI9_5_IRQn, 1u, 0u);
    HAL_NVIC_EnableIRQ(EXTI9_5_IRQn);
    HAL_NVIC_SetPriority(EXTI15_10_IRQn, 1u, 0u);
    HAL_NVIC_EnableIRQ(EXTI15_10_IRQn);
    HAL_NVIC_SetPriority(EXTI0_IRQn, 0u, 0u);
    HAL_NVIC_EnableIRQ(EXTI0_IRQn);
}

static void MX_IWDG_Init(void)
{
    /* IWDG: LSI 40 kHz / 64 = 625 Hz, reload 625 -> timeout ~1 s.
     * Main loop refresh mỗi vòng (10 ms). Nếu firmware treo, MCU tự reset.
     * Lưu ý khi debug bằng ST-Link: dừng CPU >1 s sẽ bị IWDG reset. */
    hiwdg.Instance = IWDG;
    hiwdg.Init.Prescaler = IWDG_PRESCALER_64;
    hiwdg.Init.Reload = 625u;
    if (HAL_IWDG_Init(&hiwdg) != HAL_OK) Error_Handler();
}

void HAL_MspInit(void)
{
    __HAL_RCC_AFIO_CLK_ENABLE();
    __HAL_RCC_PWR_CLK_ENABLE();
}

void HAL_TIM_PWM_MspInit(TIM_HandleTypeDef *htim)
{
    GPIO_InitTypeDef init = {0};
    if (htim->Instance == TIM1) {
        __HAL_RCC_TIM1_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();
        init.Pin = MOTOR1_PWM_PIN | MOTOR2_PWM_PIN | MOTOR3_PWM_PIN | MOTOR4_PWM_PIN;
        init.Mode = GPIO_MODE_AF_PP;
        init.Speed = GPIO_SPEED_FREQ_HIGH;
        HAL_GPIO_Init(GPIOA, &init);
    } else if (htim->Instance == TIM3) {
        __HAL_RCC_TIM3_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();
        __HAL_RCC_GPIOB_CLK_ENABLE();
        init.Pin = MOTOR1_LPWM_PIN | MOTOR2_LPWM_PIN;
        init.Mode = GPIO_MODE_AF_PP;
        init.Speed = GPIO_SPEED_FREQ_HIGH;
        HAL_GPIO_Init(GPIOA, &init);
        init.Pin = MOTOR3_LPWM_PIN | MOTOR4_LPWM_PIN;
        HAL_GPIO_Init(GPIOB, &init);
    }
}

void HAL_TIM_Encoder_MspInit(TIM_HandleTypeDef *htim)
{
    GPIO_InitTypeDef init = {0};

    if (htim->Instance == TIM2) {
        __HAL_RCC_TIM2_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();
        init.Pin = ENC1_A_PIN | ENC1_B_PIN;
        init.Mode = GPIO_MODE_INPUT;
        init.Pull = GPIO_PULLUP;
        HAL_GPIO_Init(GPIOA, &init);
    } else if (htim->Instance == TIM4) {
        __HAL_RCC_TIM4_CLK_ENABLE();
        __HAL_RCC_GPIOB_CLK_ENABLE();
        init.Pin = ENC3_A_PIN | ENC3_B_PIN;
        init.Mode = GPIO_MODE_INPUT;
        init.Pull = GPIO_PULLUP;
        HAL_GPIO_Init(GPIOB, &init);
    }
}

void HAL_UART_MspInit(UART_HandleTypeDef *huart)
{
    GPIO_InitTypeDef init = {0};

    if (huart->Instance == USART2) {
        __HAL_RCC_USART2_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();

        init.Pin = UART_TX_PIN;
        init.Mode = GPIO_MODE_AF_PP;
        init.Speed = GPIO_SPEED_FREQ_HIGH;
        HAL_GPIO_Init(GPIOA, &init);

        init.Pin = UART_RX_PIN;
        init.Mode = GPIO_MODE_INPUT;
        init.Pull = GPIO_PULLUP;
        HAL_GPIO_Init(GPIOA, &init);

        HAL_NVIC_SetPriority(USART2_IRQn, 2u, 0u);
        HAL_NVIC_EnableIRQ(USART2_IRQn);
    }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2) {
        protocol_rx_byte(rx_byte);
        HAL_UART_Receive_IT(&huart2, &rx_byte, 1u);
    }
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2) {
        HAL_UART_Receive_IT(&huart2, &rx_byte, 1u);
    }
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2) {
        protocol_tx_complete();
    }
}

void SysTick_Handler(void)
{
    HAL_IncTick();
}

void USART2_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart2);
}

void EXTI9_5_IRQHandler(void)
{
    if (__HAL_GPIO_EXTI_GET_IT(ENC4_A_PIN) != RESET) {
        __HAL_GPIO_EXTI_CLEAR_IT(ENC4_A_PIN);
        control_encoder_isr(3u);
    }
}

void EXTI15_10_IRQHandler(void)
{
    if (__HAL_GPIO_EXTI_GET_IT(ENC2_A_PIN) != RESET) {
        __HAL_GPIO_EXTI_CLEAR_IT(ENC2_A_PIN);
        control_encoder_isr(1u);
    }
}

void EXTI0_IRQHandler(void)
{
    if (__HAL_GPIO_EXTI_GET_IT(ESTOP_PIN) != RESET) {
        __HAL_GPIO_EXTI_CLEAR_IT(ESTOP_PIN);
        control_emergency_stop();
    }
}

void HardFault_Handler(void)
{
    motor_stop_all();
    __disable_irq();
    while (1) {}
}

static void Error_Handler(void)
{
    motor_stop_all();
    __disable_irq();
    while (1) {}
}