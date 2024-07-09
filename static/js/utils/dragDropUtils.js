// js/utils/dragDropUtils.js

export function cancelDrop(draggingElement, placeholder) {
    $(draggingElement).insertBefore(placeholder);
}