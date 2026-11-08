#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

/* ============================================================
 * PROTOCOL.H – API UART PROTOCOL
 * - Line-based text protocol
 * - Telemetry 50 Hz
 * ============================================================ */

void protocol_init(void);
void protocol_rx_byte(uint8_t byte);
void protocol_process(void);
uint8_t protocol_is_alive(uint32_t now_ms);
uint32_t protocol_last_rx_ms(void);
void protocol_send_telemetry(uint32_t now_ms);
void protocol_tx_complete(void);

#endif
