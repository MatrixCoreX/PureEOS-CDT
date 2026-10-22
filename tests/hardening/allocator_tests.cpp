#include <array>
#include <iostream>
#include <stdexcept>
#include <string>
#include "../../libraries/eosiolib/simple_memory.hpp"

namespace eosio::internal_use_do_not_use {
extern "C" void eosio_assert(uint32_t ok, const char* text) {
   if (!ok) throw std::runtime_error(text);
}
}

struct bounded_memory {
   static constexpr size_t page_size = 65536, max_pages = 8;
   alignas(16) std::array<char, page_size * max_pages> bytes{};
   size_t committed = 1, grows = 0;
   bool reject_growth = false;
   size_t pages() const { return committed; }
   bool grow(size_t count) {
      if (!count) throw std::runtime_error("unexpected memory.grow(0)");
      ++grows;
      if (reject_growth || count > max_pages - committed) return false;
      committed += count;
      return true;
   }
   char* pointer(size_t position) {
      if (position >= committed * page_size) throw std::runtime_error("backend pointer outside memory");
      return bytes.data() + position;
   }
   size_t offset(const void* ptr) const {
      auto address = reinterpret_cast<uintptr_t>(ptr), base = reinterpret_cast<uintptr_t>(bytes.data());
      if (address < base || address - base >= committed * page_size)
         throw std::runtime_error("backend invalid pointer");
      return address - base;
   }
};
static size_t assertions = 0;
void require(bool ok) { ++assertions; if (!ok) throw std::runtime_error("allocator assertion failed"); }
template<class F> void rejects(F&& f) {
   bool failed = false;
   try { f(); } catch (const std::runtime_error&) { failed = true; }
   require(failed);
}
int main() {
   try {
      bounded_memory memory;
      eosio::detail::simple_memory heap(memory, 16);
      require(heap.allocate(0) == nullptr);
      require(heap.zeroed(0, SIZE_MAX) == nullptr && heap.zeroed(SIZE_MAX, 0) == nullptr);
      auto* first = static_cast<char*>(heap.allocate(33));
      require(reinterpret_cast<uintptr_t>(first) % 16 == 0 && memory.grows == 0);
      for (size_t i = 0; i < 33; ++i) first[i] = char(i + 1);
      auto* grown = static_cast<char*>(heap.reallocate(first, 100));
      require(grown != first);
      for (size_t i = 0; i < 33; ++i) require(grown[i] == char(i + 1));
      require(heap.reallocate(grown, 17) == grown);
      auto* regrown = static_cast<char*>(heap.reallocate(grown, 40));
      for (size_t i = 0; i < 17; ++i) require(regrown[i] == char(i + 1));
      require(heap.reallocate(regrown, 0) == nullptr);
      require(heap.reallocate(nullptr, 0) == nullptr && heap.reallocate(nullptr, 7) != nullptr);
      auto* zeros = static_cast<char*>(heap.zeroed(64, 8));
      for (size_t i = 0; i < 512; ++i) require(zeros[i] == 0);
      rejects([&]{ heap.zeroed(SIZE_MAX, 2); });
      rejects([&]{ heap.allocate(SIZE_MAX); });
      rejects([&]{ heap.allocate(SIZE_MAX - 16); });
      rejects([&]{ heap.reallocate(memory.bytes.data() + 17, 50); });
      require(memory.grows == 0);
      auto* large = static_cast<char*>(heap.allocate(65536));
      require(memory.grows == 1 && memory.committed == 2);
      large[65535] = 'z'; require(large[65535] == 'z');
      const auto before = memory.committed;
      memory.reject_growth = true;
      rejects([&]{ heap.allocate(65536 * 2); });
      require(memory.committed == before && heap.allocate(8) != nullptr);
      memory.reject_growth = false;
      require(heap.allocate(65536 * 2) != nullptr && memory.committed <= 8);
      rejects([&]{ heap.allocate(65536 * 8); });
      require(first[32] == 33); // failed allocations did not damage old blocks

      // Exact page end is valid and must not cause a gratuitous extra page.
      bounded_memory exact_memory;
      eosio::detail::simple_memory exact(exact_memory, 16);
      require(exact.allocate(65536 - 32) != nullptr && exact_memory.grows == 0);
      require(exact.allocate(1) != nullptr && exact_memory.grows == 1);
      std::cout << "allocator assertions=" << assertions << " passed\n";
   } catch (const std::exception& error) {
      std::cerr << "after " << assertions << " assertions: " << error.what() << '\n';
      return 1;
   }
}
