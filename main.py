import l5x
def main():
    sfc_prj = l5x.Project(".\\tests\\MainProgram.L5X")
    print(sfc_prj.programs['MainProgram'].sfc.steps["2"])


if __name__ == "__main__":
    main()