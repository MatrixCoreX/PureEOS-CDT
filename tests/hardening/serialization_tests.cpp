// Exercise the real SDK headers using native assertions. WASM validation is
// deliberately a separate gate; this executable is not a VM safety audit.
#include <cstdint>
#include <cstddef>
#include <stdexcept>
#include <iostream>
#include <limits>
#include <string>
#include <eosio/datastream.hpp>

namespace eosio::internal_use_do_not_use {
extern "C" void eosio_assert(uint32_t ok, const char* text) {
   if (!ok) throw std::runtime_error(text);
}
extern "C" void eosio_assert_message(uint32_t ok, const char* text, uint32_t size) {
   if (!ok) throw std::runtime_error(std::string(text, size));
}
extern "C" void eosio_assert_code(uint32_t ok, uint64_t) {
   if (!ok) throw std::runtime_error("assert code");
}
}

static size_t assertions = 0;
static void require(bool ok) {
   ++assertions;
   if (!ok) throw std::runtime_error("regression assertion failed");
}
template<class F> void rejects(F&& operation) {
   bool rejected = false;
   try { operation(); } catch (const std::runtime_error&) { rejected = true; }
   require(rejected);
}
struct empty_element {};
struct explicit_default {
   int value;
   explicit explicit_default(int value = 7): value(value) {}
};
struct aggregate_record { explicit_default member; };
template<class S> eosio::datastream<S>& operator>>(eosio::datastream<S>& stream, aggregate_record& value) {
   stream >> value.member.value;
   return stream;
}
template<class S> eosio::datastream<S>& operator>>(eosio::datastream<S>& stream, empty_element&) {
   return stream;
}

int main() {
   using eosio::datastream;
   try {
      char bytes[16]{};
      for (uint32_t value : {0u, 127u, 128u, 16383u, 16384u, UINT32_MAX}) {
         datastream<char*> out(bytes, sizeof(bytes)); out << eosio::unsigned_int(value);
         datastream<const char*> in(bytes, out.tellp()); eosio::unsigned_int got(42); in >> got;
         require(got.value == value && in.remaining() == 0 && out.tellp() <= 5);
      }
      for (int32_t value : {INT32_MIN, -16384, -128, -1, 0, 1, 127, 16384, INT32_MAX}) {
         datastream<char*> out(bytes, sizeof(bytes)); out << eosio::signed_int(value);
         datastream<const char*> in(bytes, out.tellp()); eosio::signed_int got(42); in >> got;
         require(got.value == value && in.remaining() == 0 && out.tellp() <= 5);
      }
      uint32_t state = 1234567;
      for (unsigned i = 0; i < 10000; ++i) {
         state = state * 1664525u + 1013904223u;
         datastream<char*> out(bytes, sizeof(bytes)); out << eosio::unsigned_int(state);
         datastream<const char*> in(bytes, out.tellp()); eosio::unsigned_int got; in >> got;
         require(got.value == state);
      }
      const std::vector<std::vector<char>> malformed = {
         {}, {char(0x80)}, {char(0xff),char(0xff),char(0xff),char(0xff)},
         {char(0x80),char(0x80),char(0x80),char(0x80),char(0x10)},
         {char(0x80),char(0x80),char(0x80),char(0x80),char(0x80),char(1)},
         {char(0xff),char(0xff),char(0xff),char(0xff),char(0x7f)}
      };
      for (const auto& wire : malformed) {
         eosio::unsigned_int u(99); datastream<const char*> in(wire.data(), wire.size());
         rejects([&]{ in >> u; }); require(u.value == 99);
         eosio::signed_int s(-99); datastream<const char*> signed_in(wire.data(), wire.size());
         rejects([&]{ signed_in >> s; }); require(s.value == -99);
      }
      const char padded[] = {char(0x80), 0}; // accepted historical non-minimal zero
      datastream<const char*> padded_in(padded, 2); eosio::unsigned_int padded_zero(9);
      padded_in >> padded_zero; require(padded_zero.value == 0);

      datastream<char*> bounded(bytes, 4);
      bounded.skip(1);
      rejects([&]{ bounded.skip(4); }); require(bounded.tellp() == 1);
      rejects([&]{ bounded.skip(size_t(-1)); }); require(bounded.tellp() == 1);
      require(!bounded.seekp(size_t(-1)) && bounded.tellp() == 1);
      require(!bounded.seekp(5) && bounded.valid() && bounded.remaining() == 3);
      char copy[16]{};
      volatile size_t huge = size_t(-1);
      rejects([&]{ bounded.read(copy, huge); });
      rejects([&]{ bounded.write(copy, size_t(1) << 31); });
      rejects([&]{ bounded.write(static_cast<const void*>(copy), huge); });
      require(bounded.seekp(4) && bounded.remaining() == 0);
      rejects([&]{ char c; bounded.get(c); }); rejects([&]{ bounded.put('x'); });
      datastream<char*> null_stream(nullptr, 0);
      require(null_stream.pos() == nullptr && null_stream.valid());
      require(null_stream.read(nullptr, 0) && null_stream.write(static_cast<const void*>(nullptr), 0));
      rejects([&]{ datastream<char*> bad(nullptr, 1); });

      datastream<size_t> counter(std::numeric_limits<size_t>::max());
      rejects([&]{ counter.skip(1); }); rejects([&]{ counter.put('x'); });
      require(counter.tellp() == std::numeric_limits<size_t>::max());

      const char forged[] = {char(0x80),char(0x80),char(0x04)}; // 65536 with no body
      std::vector<char> values{'x'}; datastream<const char*> vector_in(forged, 3);
      rejects([&]{ vector_in >> values; }); require(values.size() == 1);
      std::string text("old"); datastream<const char*> string_in(forged, 3);
      rejects([&]{ string_in >> text; }); require(text == "old");
      std::vector<std::string> nested; datastream<const char*> nested_in(forged, 3);
      rejects([&]{ nested_in >> nested; }); require(nested.empty());
      std::list<char> linked{'a'}; datastream<const char*> list_in(forged, 3);
      rejects([&]{ list_in >> linked; }); require(linked.size() == 1 && linked.front() == 'a');
      std::deque<char> queue{'b'}; datastream<const char*> queue_in(forged, 3);
      rejects([&]{ queue_in >> queue; }); require(queue.size() == 1 && queue.front() == 'b');
      const char empty_wire[] = {3}; datastream<const char*> empty_in(empty_wire, 1);
      std::vector<empty_element> empty; empty_in >> empty;
      require(empty.size() == 3 && empty_in.remaining() == 0);
      char aggregate_wire[5] = {1, 42, 0, 0, 0};
      datastream<const char*> aggregate_in(aggregate_wire, sizeof(aggregate_wire));
      std::vector<aggregate_record> records; aggregate_in >> records;
      require(records.size() == 1 && records.front().member.value == 42);
      const std::vector<uint64_t> original{0, 1, UINT64_MAX};
      datastream<char*> small(bytes, sizeof(bytes));
      rejects([&]{ small << original; });
      const auto encoded = eosio::pack(original);
      require(eosio::unpack<std::vector<uint64_t>>(encoded.data(), encoded.size()) == original);
      std::cout << "serialization assertions=" << assertions << " passed\n";
   } catch (const std::exception& error) {
      std::cerr << "after " << assertions << " assertions: " << error.what() << '\n';
      return 1;
   }
}
