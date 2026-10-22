#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include "core/eosio/check.hpp"

namespace eosio::detail {

// Instance-local bump allocation. Backend supplies page count/growth and
// offset<->pointer conversion; it never shares mutable memory between VMs.
template<class Backend>
class simple_memory {
   static constexpr size_t page_size = 65536, alignment = 16, header_bytes = 16;
   struct header { size_t size, guard; };
   static_assert(sizeof(header) <= header_bytes);
   Backend& memory_;
   const size_t heap_;
   size_t cursor_;

   static size_t aligned(size_t value) {
      eosio::check(value <= std::numeric_limits<size_t>::max() - (alignment - 1), "allocation size overflow");
      return (value + alignment - 1) & ~(alignment - 1);
   }
   static size_t guard(size_t offset, size_t size) {
      return offset ^ size ^ size_t(0x6d616c6c);
   }
   void ensure_capacity(size_t end) {
      const size_t needed = end / page_size + (end % page_size != 0);
      const size_t current = memory_.pages();
      if (needed > current)
         eosio::check(memory_.grow(needed - current), "failed to allocate pages");
   }
   header get_header(void* ptr) const {
      const size_t offset = memory_.offset(ptr);
      eosio::check(offset >= heap_ && offset - heap_ >= header_bytes &&
         offset < cursor_ && offset % alignment == 0, "invalid realloc pointer");
      header old;
      std::memcpy(&old, memory_.pointer(offset - header_bytes), sizeof(old));
      eosio::check(old.size <= cursor_ - offset && old.guard == guard(offset, old.size),
         "invalid realloc allocation");
      return old;
   }
public:
   simple_memory(Backend& memory, size_t heap)
      : memory_(memory), heap_(aligned(heap)), cursor_(heap_) {}

   void* allocate(size_t size) {
      if (!size) return nullptr;
      constexpr auto maximum = std::numeric_limits<size_t>::max();
      eosio::check(cursor_ <= maximum - header_bytes, "allocation size overflow");
      const size_t offset = cursor_ + header_bytes;
      eosio::check(size <= maximum - offset, "allocation size overflow");
      const size_t next = aligned(offset + size);
      // Publish neither cursor nor header until growth has succeeded.
      ensure_capacity(next);
      const header value{size, guard(offset, size)};
      std::memcpy(memory_.pointer(offset - header_bytes), &value, sizeof(value));
      cursor_ = next;
      return memory_.pointer(offset);
   }

   void* zeroed(size_t count, size_t size) {
      eosio::check(!size || count <= std::numeric_limits<size_t>::max() / size,
         "calloc size overflow");
      const size_t bytes = count * size;
      auto* ptr = allocate(bytes);
      if (bytes) std::memset(ptr, 0, bytes);
      return ptr;
   }

   void* reallocate(void* ptr, size_t size) {
      if (!ptr) return allocate(size);
      const auto old = get_header(ptr);
      if (!size) return nullptr; // free remains instance-lifetime/no-op
      if (size <= old.size) {
         const auto offset = memory_.offset(ptr);
         const header value{size, guard(offset, size)};
         std::memcpy(memory_.pointer(offset - header_bytes), &value, sizeof(value));
         return ptr;
      }
      void* next = allocate(size);
      std::memcpy(next, ptr, old.size);
      return next;
   }
};
} // namespace eosio::detail
