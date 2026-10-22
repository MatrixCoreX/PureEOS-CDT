#include <memory>
#include "core/eosio/check.hpp"
#include "simple_memory.hpp"

#ifdef EOSIO_NATIVE
   extern "C" {
      size_t _current_memory();
      size_t _grow_memory(size_t);
   }
#define CURRENT_MEMORY _current_memory()
#define GROW_MEMORY(X) _grow_memory(X)
#else
#define CURRENT_MEMORY __builtin_wasm_memory_size(0)
#define GROW_MEMORY(X) __builtin_wasm_memory_grow(0, X)
#endif

namespace eosio {
   struct wasm_memory {
      size_t pages() const { return CURRENT_MEMORY; }
      bool grow(size_t count) { return GROW_MEMORY(count) != size_t(-1); }
      char* pointer(size_t offset) const { return reinterpret_cast<char*>(offset); }
      size_t offset(const void* ptr) const { return reinterpret_cast<size_t>(ptr); }
   };
   static size_t initial_heap() {
      volatile uintptr_t heap_base = 0; // linker places the heap pointer at address 0
      return *reinterpret_cast<size_t*>(heap_base);
   }
   wasm_memory _ds_memory;
   detail::simple_memory<wasm_memory> _dsmalloc(_ds_memory, initial_heap());
} // ns eosio

extern "C" {

void* malloc(size_t size) {
   return eosio::_dsmalloc.allocate(size);
}

void* memset(void*,int,size_t);
void* calloc(size_t count, size_t size) {
   return eosio::_dsmalloc.zeroed(count, size);
}

void* realloc(void* ptr, size_t size) {
   return eosio::_dsmalloc.reallocate(ptr, size);
}

void free(void* ptr) {}
}

