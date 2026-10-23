// Standalone project scaffolding; does not need the compiler's LLVM runtime.
#include <exception>
#include <filesystem>
#include <iostream>
#include <fstream>
#include <sstream>
#include <regex>
#include <stdexcept>
#include <string>

#ifndef AIC_CDT_INIT_VERSION
#define AIC_CDT_INIT_VERSION "@VERSION_FULL@"
#endif

namespace fs = std::filesystem;

struct project {
   std::string project_name;
   std::string path;
   bool        bare;

   project( const std::string& pn, const std::string& p, bool b ) : project_name(pn), path(p), bare(b) {
      if (!fs::create_directory(path))
         throw std::runtime_error("Project already exists; refusing to overwrite: " + path);
      if (!bare) {
         fs::create_directory(path+"/src");
         fs::create_directory(path+"/include");
         fs::create_directory(path+"/ricardian");
         fs::create_directory(path+"/build");
      }
   }

   const std::string cpp = "#include <@.hpp>\n"
                           "ACTION @::hi( name nm ) {\n"
                           "   /* fill in action body */\n"
                           "   print_f(\"Name : %\\n\",nm);\n"
                           "}";

   const std::string hpp = "#include <eosio/eosio.hpp>\n"
                           "using namespace eosio;\n\n"
                           "CONTRACT @ : public contract {\n"
                           "   public:\n"
                           "      using contract::contract;\n\n"
                           "      ACTION hi( name nm );\n\n"
                           "      using hi_action = action_wrapper<\"hi\"_n, &@::hi>;\n"
                           "};";

   const std::string ricardian = "<h1 class=\"contract\"> hi </h1>\n\n"
                                 "Stub for hi action's ricardian contract";

   const std::string cmake = "cmake_minimum_required(VERSION 3.20)\n"
                             "project(@ LANGUAGES CXX)\n\n"
                             "find_package(cdt CONFIG REQUIRED)\n\n"
                             "add_contract( @ @ @.cpp )\n"
                             "target_include_directories( @ PUBLIC ${CMAKE_SOURCE_DIR}/../include )\n"
                             "target_ricardian_directory( @ ${CMAKE_SOURCE_DIR}/../ricardian )";

   const std::string cmake_extern = "cmake_minimum_required(VERSION 3.20)\n"
                                    "project(@ LANGUAGES NONE)\n"
                                    "include(ExternalProject)\n"
                                    "# if no cdt root is given use default path\n"
                                    "if(CDT_ROOT STREQUAL \"\" OR NOT CDT_ROOT)\n"
                                    "   find_package(cdt CONFIG REQUIRED)\n"
                                    "endif()\n\n"
                                    "ExternalProject_Add(\n"
                                    "   @_project\n"
                                    "   SOURCE_DIR ${CMAKE_SOURCE_DIR}/src\n"
                                    "   BINARY_DIR ${CMAKE_BINARY_DIR}/@\n"
                                    "   CMAKE_ARGS \"-DCMAKE_TOOLCHAIN_FILE=${CDT_ROOT}/lib/cmake/cdt/CDTWasmToolchain.cmake\"\n"
                                    "              \"-Dcdt_DIR=${CDT_ROOT}/lib/cmake/cdt\"\n"
                                    "   UPDATE_COMMAND \"\"\n"
                                    "   PATCH_COMMAND \"\"\n"
                                    "   TEST_COMMAND \"\"\n"
                                    "   INSTALL_COMMAND \"\"\n"
                                    "   BUILD_ALWAYS 1\n"
                                    ")";

   const std::string readme_cmake = "--- @ Project ---\n\n"
                                    " - How to Build -\n"
                                    "   - cd to 'build' directory\n"
                                    "   - run 'cmake .. -DCMAKE_PREFIX_PATH=/path/to/your/cdt/sdk'\n"
                                    "   - run the command 'make'\n\n"
                                    " - After build -\n"
                                    "   - The built smart contract is under the '@' directory in the 'build' directory\n"
                                    "   - You can then do a 'set contract' action with 'cleos' and point in to the './build/@' directory\n\n"
                                    " - Additions to CMake should be done to the CMakeLists.txt in the './src' directory and not in the top level CMakeLists.txt";

   const std::string readme_bare = " --- @ Project ---\n\n"
                                   " - How to Build -\n"
                                   "   - run the command 'cdt-cpp -abigen -o @.wasm @.cpp'\n";

   std::string replace_name( const std::string& in ) {
      std::stringstream ss;
      for ( char c : in ) {
         if (c == '@')
            ss << project_name;
         else
            ss << c;
      }
      return ss.str();
   }

   std::string replace_include_type( const std::string& in ) {
      std::stringstream ss;
      for ( char c : in ) {
         if ((c == '<' || c == '>') && bare)
            ss << '"';
         else
            ss << c;
      }
      return ss.str();
   }

   void write_cpp() {
      std::ofstream cpp_out;
      cpp_out.exceptions(std::ofstream::failbit | std::ofstream::badbit);
      if (bare)
         cpp_out.open(path+"/"+project_name+".cpp");
      else
         cpp_out.open(path+"/src/"+project_name+".cpp");
      cpp_out << replace_include_type(replace_name(cpp));
      cpp_out.close();
   }
   void write_hpp() {
      std::ofstream hpp_out;
      hpp_out.exceptions(std::ofstream::failbit | std::ofstream::badbit);
      if (bare)
         hpp_out.open(path+"/"+project_name+".hpp");
      else
         hpp_out.open(path+"/include/"+project_name+".hpp");
      hpp_out << replace_name(hpp);
      hpp_out.close();
   }
   void write_cmake() {
      if (!bare) {
         std::ofstream cmake_out(path+"/src/CMakeLists.txt");
         cmake_out.exceptions(std::ofstream::failbit | std::ofstream::badbit);
         cmake_out << replace_name(cmake);
         cmake_out.close();
      }
   }
   void write_cmake_extern() {
      if (!bare) {
         std::ofstream cmake_out(path+"/CMakeLists.txt");
         cmake_out.exceptions(std::ofstream::failbit | std::ofstream::badbit);
         cmake_out << replace_name(cmake_extern);
         cmake_out.close();
      }
   }
   void write_ricardian() {
      std::ofstream rc_out;
      rc_out.exceptions(std::ofstream::failbit | std::ofstream::badbit);
      if (bare)
         rc_out.open(path+"/"+project_name+".contracts.md");
      else
         rc_out.open(path+"/ricardian/"+project_name+".contracts.md");
      rc_out << ricardian;
      rc_out.close();
   }
   void write_readme() {
      std::ofstream readme_out(path+"/README.txt");
      readme_out.exceptions(std::ofstream::failbit | std::ofstream::badbit);
      if (bare) {
         readme_out << replace_name(readme_bare);
      } else {
         readme_out << replace_name(readme_cmake);
      }
      readme_out.close();
   }

};

int main(int argc, const char **argv) {
   try {
      std::string project_name, output_dir = ".";
      bool bare_opt = false, project_seen = false, path_seen = false;
      for (int i = 1; i < argc; ++i) {
         const std::string arg = argv[i];
         if (arg == "--help" || arg == "--help-list") {
            std::cout << "Usage: cdt-init --project=NAME [--path=EXISTING_DIRECTORY] [--bare]\n"
                         "Creates a NEW project directory; never overwrites an existing one.\n";
            return 0;
         }
         if (arg == "--version") {
            std::cout << "AIC CDT " << AIC_CDT_INIT_VERSION << " (cdt-init)\n";
            return 0;
         }
         if (arg == "--bare") { bare_opt = true; continue; }
         auto value = [&](const std::string& name, std::string& into, bool& seen) {
            if (arg != name && arg.rfind(name + "=", 0) != 0) return false;
            if (seen) throw std::runtime_error("Duplicate option: " + name);
            seen = true;
            if (arg == name) {
               if (++i >= argc) throw std::runtime_error("Missing value for " + name);
               into = argv[i];
            } else into = arg.substr(name.size() + 1);
            if (into.empty()) throw std::runtime_error("Empty value for " + name);
            return true;
         };
         if (value("--project", project_name, project_seen) || value("--path", output_dir, path_seen)) continue;
         throw std::runtime_error("Unknown option: " + arg);
      }
      if (!std::regex_match(project_name, std::regex("^[_a-zA-Z][_a-zA-Z0-9]*$"))) {
         throw std::runtime_error("ERROR: invalid identifier: " + project_name + " (ensure that it is a valid C++ identifier)");
      }
      const auto parent = fs::canonical(output_dir);
      if (!fs::is_directory(parent)) throw std::runtime_error("Project parent is not a directory");
      const std::string path = (parent/project_name).string();

      project proj(project_name, path, bare_opt);
      proj.write_hpp();
      proj.write_cpp();
      proj.write_cmake();
      proj.write_cmake_extern();
      proj.write_ricardian();
      proj.write_readme();
   } catch ( std::exception& e ) {
      std::cerr << e.what() << "\n";
      return 1;
   }

   return 0;
}
