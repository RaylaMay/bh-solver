#ifndef BH_PLUGIN_H
#define BH_PLUGIN_H

/* BH solver extension ABI v1 foundation.
 *
 * This header declares a stable C ABI for precompiled C++ extensions. It does
 * not grant trust, load a library, approve numerical output, or bundle a compiler.
 * Callers must validate the separate PluginManifest and retain execution provenance.
 */

#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32)
#define BH_PLUGIN_EXPORT __declspec(dllexport)
#else
#define BH_PLUGIN_EXPORT __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define BH_PLUGIN_ABI_VERSION 1u

typedef enum bh_plugin_status_v1 {
    BH_PLUGIN_OK = 0,
    BH_PLUGIN_REJECTED = 1,
    BH_PLUGIN_FAILED = 2,
    BH_PLUGIN_BUFFER_TOO_SMALL = 3
} bh_plugin_status_v1;

typedef struct bh_plugin_bytes_v1 {
    const uint8_t *data;
    size_t size;
} bh_plugin_bytes_v1;

typedef struct bh_plugin_mutable_bytes_v1 {
    uint8_t *data;
    size_t capacity;
    size_t size;
} bh_plugin_mutable_bytes_v1;

typedef struct bh_plugin_host_v1 {
    uint32_t abi_version;
    void *context;
    void (*log_utf8)(void *context, uint32_t severity, const char *message, size_t size);
} bh_plugin_host_v1;

/* Return a UTF-8 bh-plugin-manifest-v1 JSON document. */
BH_PLUGIN_EXPORT bh_plugin_status_v1 bh_plugin_query_v1(
    bh_plugin_mutable_bytes_v1 *manifest_json
);

/* Execute one stable-API request encoded by the language-neutral worker protocol.
 * The host owns all buffers. The plugin must not retain pointers after return.
 */
BH_PLUGIN_EXPORT bh_plugin_status_v1 bh_plugin_execute_v1(
    const bh_plugin_host_v1 *host,
    bh_plugin_bytes_v1 request_json,
    bh_plugin_mutable_bytes_v1 *response_json
);

#ifdef __cplusplus
}
#endif

#endif
