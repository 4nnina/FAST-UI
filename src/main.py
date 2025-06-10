import sys
import os
import pandas as pd
import copy
import random
from utils import computeParetoFront, acceptanceProbability, updateParetoSet
from global_sol.utils_global import perturbate
from global_sol.data_classes_global import GlobalUniversity
import json

def performSaUI(curr_sol, paretoSet, paretoFront, initialTemp, finalTemp, alpha, maxPerturbation, heuristic = False):  #new
    temperature = initialTemp
    c = 0
    
    while temperature > finalTemp:
        for _ in range(maxPerturbation):
            perturbSol = perturbate(curr_sol)
            
            if perturbSol == curr_sol:
                continue

            prob = acceptanceProbability(curr_sol, perturbSol, temperature, paretoFront)

            if random.uniform(0, 1) < prob:
                updateParetoSet(perturbSol, paretoSet)
                curr_sol = copy.deepcopy(perturbSol)

        best_sol = max(paretoSet, key=lambda x: x.fairness_score())
        print("\n" + "="*80)
        print(f"Temperature: {temperature:.2f}")
        print(best_sol.getSingleFairnessScore())
        print(f"Current Fairness Score: {best_sol.fairness_score()}")
        print("="*80)

        
        c += 1
        temperature = initialTemp - alpha * c

    return paretoSet

def getBestSolUI(curr_sol, initialTemp, finalTemp, alpha, maxPerturbation, heuristic = False):
    sol = copy.deepcopy(curr_sol)
    paretoSet = set()
    paretoSet.add(sol)
    paretoFront = computeParetoFront(paretoSet)

    print(f"Initial Fairness Score: {sol.fairness_score()}")
    
    paretoSet = performSaUI(sol, paretoSet, paretoFront, initialTemp, finalTemp, alpha, maxPerturbation, heuristic)

    best_sol = max(paretoSet, key=lambda x: x.fairness_score())
    print("\n" + "="*80)
    print("FINAL RESULT:")
    print(best_sol.getSingleFairnessScore())
    print(f"Final Fairness Score: {best_sol.fairness_score()}")
    print("="*80)     

    return best_sol

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(current_dir, '..', 'dataset', 'university')
    csv_path = os.path.join(dataset_path, 'lecture_timeslots.csv')

    possible_paths = [
        os.path.join(current_dir, '..', 'dataset', 'university', 'lecture_timeslots.csv')
    ]
    
    csv_path = None
    for path in possible_paths:
        if os.path.exists(path):
            csv_path = path
            break
    
    if not csv_path:
        print("ERROR: Could not find lecture_timeslots.csv in any of these locations:")
        for path in possible_paths:
            print(f"- {path}")
        sys.exit(1)

    schedule = pd.read_csv(csv_path)

    degrees = [
        "Laurea in Biotecnologie [385] Corsi di laurea - UNICO",
        "Laurea in Informatica [420] Corsi di laurea - UNICO",
        "Laurea in Bioinformatica [419] Corsi di laurea - UNICO"
    ]

    schedule = schedule[schedule["degree"].isin(degrees)]

    prof = schedule["prof_id"].unique().tolist()
    dict_degree = {degree: [1, 2, 3] for degree in degrees}

    print("Creating initial solution...")
    obj = GlobalUniversity(prof, dict_degree)

    def process_section(section):
        section_data = {
            "professors": [],
            "degrees": {},
            "final_fairness": None,
            "Fairness < 100%": 0,
            "Worst Percentage": 100
        }

        degree_mapping = {
            "Laurea in Biotecnologie [385] Corsi di laurea - UNICO": "Bio",
            "Laurea in Informatica [420] Corsi di laurea - UNICO": "Inf",
            "Laurea in Bioinformatica [419] Corsi di laurea - UNICO": "BioInf"
        }
        
        lines = section.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("Prof Name:"):
                parts = line.split('\t')
                if len(parts) >= 3:
                    prof_name = parts[0].split(": ")[1].strip()
                    fairness_score = float(parts[1].split(": ")[1].strip())
                    percentage = float(parts[2].strip().replace("%", ""))
                    
                    if percentage < 100:
                        section_data["Fairness < 100%"] += 1
                    if percentage < section_data["Worst Percentage"]:
                        section_data["Worst Percentage"] = percentage
                    
                    section_data["professors"].append({
                        "name": prof_name,
                        "fairness": fairness_score,
                        "percentage": percentage
                    })
            
            elif line.startswith("Degree Name:"):
                parts = line.split('\t')
                if len(parts) >= 3:
                    original_name = parts[0].split(": ")[1].strip()
                    year = int(parts[1].split(": ")[1].strip())
                    fairness_score = float(parts[2].split(": ")[1].strip())
                    
                    short_name = degree_mapping.get(original_name, original_name)
                    key = f"Fairness Score year {year} {short_name}"
                    section_data["degrees"][key] = fairness_score
            
            elif "Fairness Score:" in line and ("Initial" in line or "Current" in line or "Final" in line):
                section_data["final_fairness"] = float(line.split(": ")[1].strip())
        
        return section_data

    class RealTimeOutputProcessor:
        def __init__(self, output_dir):
            self.output_dir = output_dir
            self.buffer = ""
            self.section_count = 0
            self.terminal = sys.stdout
            os.makedirs(output_dir, exist_ok=True)
        
        def write(self, message):
            self.terminal.write(message)
            self.buffer += message
            
            if "================================================================================\n" in self.buffer:
                self._process_sections()
        
        def flush(self):
            self.terminal.flush()
        
        def _process_sections(self):
            while "================================================================================\n" in self.buffer:
                section_end = self.buffer.find("================================================================================\n") + len("================================================================================\n")
                section = self.buffer[:section_end]
                self.buffer = self.buffer[section_end:]
                
                if "Detailed Fairness Score" in section and "FINAL RESULT" not in section:
                    self._save_section(section)
        
        def _save_section(self, section_text):
            try:
                iteration_data = process_section(section_text)
                if not iteration_data:
                    return
                    
                self.section_count += 1
                
                json_filename = f"fairness_data_{self.section_count:03d}.json"
                json_path = os.path.join(self.output_dir, json_filename)
                
                with open(json_path, 'w') as f:
                    json.dump(iteration_data, f, indent=4)
                
                print(f"\n[SAVED] Iteration {self.section_count} saved to: {json_filename}")
            except Exception as e:
                print(f"\n[ERROR] Failed to save section: {str(e)}")

    def run_optimization(obj):
        print("\nStarting optimization process...")
            
        # base_dir = os.path.join(os.path.expanduser("~"), "Desktop", "orari")
            
        # specific_folder = "university_schedules_stats"
            
        # output_dir = os.path.join(base_dir, specific_folder)

        base_dir = os.path.join(os.getcwd())
        specific_folder = "university_schedules_stats"
        output_dir = os.path.join(base_dir, '..', specific_folder)


        try:
            os.makedirs(output_dir, exist_ok=True)
            print(f"\n[INFO] Created output directory: {output_dir}")
        except Exception as e:
            print(f"\n[ERROR] Failed to create directory: {str(e)}")
            return

        processor = RealTimeOutputProcessor(output_dir)
            
        original_stdout = sys.stdout
        sys.stdout = processor
            
        try:
            best_solution = getBestSolUI(copy.deepcopy(obj), 50, 5, 0.5, 50)
            processor._process_sections()
        except Exception as e:
            print(f"\n[ERROR] Optimization failed: {str(e)}")
        finally:
            sys.stdout = original_stdout
            
        print(f"\nOptimization completed successfully!")
        print(f"Total files created: {processor.section_count}")
        print(f"All files saved in: {output_dir}")

    run_optimization(obj)

if __name__ == "__main__":
    main()
